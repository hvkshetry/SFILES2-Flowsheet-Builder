import streamlit as st
import networkx as nx
import matplotlib.pyplot as plt
import io
import sys
import os

# Create a simplified Flowsheet class to avoid pyflowsheet dependency
class Flowsheet:
    def __init__(self):
        self.state = nx.DiGraph()
        self.sfiles = ""
    
    def add_unit(self, unique_name):
        self.state.add_node(unique_name)
    
    def add_stream(self, from_unit, to_unit, tags=None):
        if tags is None:
            tags = {"he": [], "col": [], "signal": []}
        self.state.add_edge(from_unit, to_unit, tags=tags)
    
    def create_from_sfiles(self, sfiles_string, overwrite_nx=True):
        # A very basic SFILES parser for demonstration
        self.sfiles = sfiles_string
        self.state = nx.DiGraph()
        
        # Parse units (anything in parentheses)
        import re
        units = re.findall(r'\(([^()]+)\)', sfiles_string)
        
        # Add all units without automatically connecting them
        for unit in units:
            self.add_unit(unit)
            
        # We'll skip the automatic connections between units
        # The user will explicitly add connections through the UI
    
    def convert_to_sfiles(self, version="v2"):
        # A very basic converter for demonstration
        # Get all nodes in a reasonable order (using topological sort if possible)
        try:
            nodes = list(nx.topological_sort(self.state))
        except nx.NetworkXUnfeasible:
            # If there's a cycle, just use the nodes in any order
            nodes = list(self.state.nodes())
        
        # Build a simple SFILES string (just units in parentheses)
        sfiles = ""
        for node in nodes:
            sfiles += f"({node})"
            
            # Add any outgoing edges
            successors = list(self.state.successors(node))
            if len(successors) > 1:
                # Handle branching (multiple outputs)
                sfiles += "["
                for i, succ in enumerate(successors):
                    if i > 0:
                        sfiles += "|"
                    # We don't add the successor here, it will be added in its own iteration
                sfiles += "]"
        
        self.sfiles = sfiles
        return self.sfiles

# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------

# Function to get existing connections
def get_existing_connections() -> list:
    """
    Returns a list of existing connections from the session state.
    """
    connections = []
    
    # Use the connections stored in session state
    if "connections" in st.session_state:
        for from_unit, to_unit, tags in st.session_state.connections:
            connections.append({
                'from': from_unit,
                'to': to_unit,
                'tags': tags
            })
    
    return connections

# Function to delete a connection
def delete_connection(from_unit: str, to_unit: str) -> None:
    """
    Delete a connection from the session state.
    """
    if "connections" in st.session_state:
        # Find and remove the connection
        st.session_state.connections = [(f, t, tags) for f, t, tags in st.session_state.connections 
                                       if not (f == from_unit and t == to_unit)]
def render_flowsheet_graph(sfiles_string: str) -> plt.Figure:
    """
    Given an SFILES string and connections list, render the flowsheet graph.
    """
    flowsheet = Flowsheet()
    flowsheet.create_from_sfiles(sfiles_string, overwrite_nx=True)
    
    # Add connections from the session state
    if "connections" in st.session_state:
        for from_unit, to_unit, tags in st.session_state.connections:
            # Parse tags if they're in string format
            if isinstance(tags, str):
                parsed_tags = [t.strip() for t in tags.split(",") if t.strip()]
                tag_dict = {"he": [], "col": parsed_tags, "signal": []}
            else:
                tag_dict = {"he": [], "col": [], "signal": []}
                
            # Add the connection to the graph
            flowsheet.add_stream(from_unit, to_unit, tags=tag_dict)
    
    # Now we can do a basic matplotlib drawing from flowsheet.state
    G = flowsheet.state
    fig, ax = plt.subplots(figsize=(10, 6))
    pos = nx.spring_layout(G)  # or any layout
    nx.draw(G, pos, with_labels=True, ax=ax, node_color='lightblue', edge_color='gray', 
            font_weight='bold', node_size=2000, font_size=10)
    
    # Draw edge labels if needed
    edge_labels = {}
    for u, v, data in G.edges(data=True):
        if 'tags' in data and data['tags']:
            tags = []
            for category, items in data['tags'].items():
                if items:  # Only add non-empty tag categories
                    tags.extend(items)
            if tags:
                edge_labels[(u, v)] = ', '.join(tags)
    
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, ax=ax)
    
    ax.set_title("Current Flowsheet Graph")
    plt.tight_layout()
    return fig

def add_unit_to_sfiles(current_sfiles: str, unit_name: str, unit_type: str="") -> str:
    """
    Parse the existing SFILES -> add the unit -> rebuild SFILES.
    """
    # 1) Build flowsheet from existing SFILES
    fs = Flowsheet()
    if current_sfiles.strip():
        fs.create_from_sfiles(current_sfiles, overwrite_nx=True)

    # 2) Add the new unit
    # If unit_name already contains unit_type (e.g. "dist-1"), use it as is
    # Otherwise, combine unit_type and unit_name (e.g. "dist-1")
    if unit_type and "-" not in unit_name:
        final_name = f"{unit_type}-{unit_name}"
    else:
        final_name = unit_name

    fs.add_unit(unique_name=final_name)

    # 3) Convert back to SFILES
    fs.convert_to_sfiles(version="v2")
    return fs.sfiles

def add_stream_to_sfiles(current_sfiles: str, from_unit: str, to_unit: str, tags: str="") -> str:
    """
    Add a stream to the flowsheet and update the connections list.
    'tags' could be comma-separated. e.g. "hot_in,cold_out"
    """
    fs = Flowsheet()
    if current_sfiles.strip():
        fs.create_from_sfiles(current_sfiles, overwrite_nx=True)

    # Basic parse of user-defined tags
    parsed_tags = [t.strip() for t in tags.split(",") if t.strip()]
    # Store tags under appropriate categories
    tag_dict = {"he": [], "col": parsed_tags, "signal": []}

    fs.add_stream(from_unit, to_unit, tags=tag_dict)
    
    # Add this connection to our session state
    if "connections" in st.session_state:
        st.session_state.connections.append((from_unit, to_unit, tags))
    
    fs.convert_to_sfiles(version="v2")
    return fs.sfiles

def get_existing_units(sfiles_string: str) -> list:
    """
    Parse the SFILES string and return a list of existing unit names.
    """
    if not sfiles_string.strip():
        return []
        
    fs = Flowsheet()
    fs.create_from_sfiles(sfiles_string, overwrite_nx=True)
    return list(fs.state.nodes())

def create_branch_in_sfiles(current_sfiles: str, from_unit: str, to_units: list, tags_list: list=None) -> str:
    """
    Create a branching structure and update connections list.
    """
    fs = Flowsheet()
    if current_sfiles.strip():
        fs.create_from_sfiles(current_sfiles, overwrite_nx=True)
    
    # If tags_list is None, initialize it with empty dicts
    if tags_list is None:
        tags_list = [""] * len(to_units)
    
    # Add each branch to the flowsheet and connections list
    for i, to_unit in enumerate(to_units):
        fs.add_stream(from_unit, to_unit, tags={})
        
        # Also add to connections list
        if "connections" in st.session_state:
            st.session_state.connections.append((from_unit, to_unit, tags_list[i] if i < len(tags_list) else ""))
    
    fs.convert_to_sfiles(version="v2")
    return fs.sfiles

def create_join_in_sfiles(current_sfiles: str, from_units: list, to_unit: str, tags_list: list=None) -> str:
    """
    Create a joining structure and update connections list.
    """
    fs = Flowsheet()
    if current_sfiles.strip():
        fs.create_from_sfiles(current_sfiles, overwrite_nx=True)
    
    # If tags_list is None, initialize it with empty strings
    if tags_list is None:
        tags_list = [""] * len(from_units)
    
    # Add each incoming stream to the flowsheet and connections list
    for i, from_unit in enumerate(from_units):
        fs.add_stream(from_unit, to_unit, tags={})
        
        # Also add to connections list
        if "connections" in st.session_state:
            st.session_state.connections.append((from_unit, to_unit, tags_list[i] if i < len(tags_list) else ""))
    
    fs.convert_to_sfiles(version="v2")
    return fs.sfiles

def create_cycle_in_sfiles(current_sfiles: str, from_unit: str, to_unit: str, tags: str="") -> str:
    """
    Create a cycle (recycle) and update connections list.
    """
    fs = Flowsheet()
    if current_sfiles.strip():
        fs.create_from_sfiles(current_sfiles, overwrite_nx=True)
    
    # Add the recycle stream to the flowsheet
    fs.add_stream(from_unit, to_unit, tags={})
    
    # Also add to connections list
    if "connections" in st.session_state:
        st.session_state.connections.append((from_unit, to_unit, tags))
    
    fs.convert_to_sfiles(version="v2")
    return fs.sfiles

# ----------------------------------------------------------------------------
# Streamlit UI
# ----------------------------------------------------------------------------

st.set_page_config(
    page_title="SFILES 2.0 Flowsheet Builder",
    page_icon="🏭",
    layout="wide",
)

st.title("SFILES 2.0 Flowsheet Builder")
st.markdown("Create a flowsheet by adding units and streams. The SFILES 2.0 notation is updated automatically.")

if "sfiles_string" not in st.session_state:
    # Start with an empty flowsheet
    st.session_state.sfiles_string = ""
    
# Initialize form_key if not already present
if "form_key" not in st.session_state:
    st.session_state.form_key = 0
    
# Initialize connections list if not already present
if "connections" not in st.session_state:
    st.session_state.connections = []

# Layout with two columns
col1, col2 = st.columns([1, 2])

with col1:
    # Add Unit form
    st.subheader("Add a Unit")
    unit_type = st.text_input("Unit Type (e.g. dist, hex, reactor)", key=f"unit_type_{st.session_state.get('form_key', 0)}")
    unit_name = st.text_input("Unique Name (e.g. 1, 2, or full name like dist-1)", key=f"unit_name_{st.session_state.get('form_key', 0)}")

    if st.button("Add Unit", key=f"add_unit_{st.session_state.get('form_key', 0)}"):
        if unit_name.strip():
            # Update the SFILES
            new_sfiles = add_unit_to_sfiles(st.session_state.sfiles_string, unit_name, unit_type)
            st.session_state.sfiles_string = new_sfiles
            # Increment form key to reset form inputs
            st.session_state['form_key'] = st.session_state.get('form_key', 0) + 1
            # Force rerun to show the updated form
            st.rerun()
        else:
            st.warning("Please provide a unique name for the unit.")

    # Get existing units for dropdowns
    existing_units = get_existing_units(st.session_state.sfiles_string)
    
    # Add Stream form
    st.subheader("Add a Stream")
    if not existing_units:
        st.info("Add at least one unit first.")
    else:
        from_unit = st.selectbox("From Unit", existing_units, key=f"from_unit_{st.session_state.get('form_key', 0)}")
        to_unit = st.selectbox("To Unit", existing_units, key=f"to_unit_{st.session_state.get('form_key', 0)}")
        tags = st.text_input("Stream Tags (comma-separated, e.g. hot_in,cold_out)", key=f"tags_{st.session_state.get('form_key', 0)}")

        if st.button("Add Stream", key=f"add_stream_{st.session_state.get('form_key', 0)}"):
            if from_unit != to_unit:
                new_sfiles = add_stream_to_sfiles(st.session_state.sfiles_string, from_unit, to_unit, tags)
                st.session_state.sfiles_string = new_sfiles
                # Increment form key to reset form inputs
                st.session_state['form_key'] = st.session_state.get('form_key', 0) + 1
                # Force rerun to show the updated form
                st.rerun()
            else:
                st.warning("From Unit and To Unit cannot be the same.")

    # Manage Existing Connections
    if existing_units:
        st.subheader("Manage Existing Connections")
        
        # Get existing connections
        connections = get_existing_connections()
        
        if not connections:
            st.info("No connections exist yet. Add a stream to create connections.")
        else:
            st.write("Current connections:")
            for i, conn in enumerate(connections):
                cols = st.columns([3, 3, 3, 1])
                with cols[0]:
                    st.text(f"From: {conn['from']}")
                with cols[1]:
                    st.text(f"To: {conn['to']}")
                with cols[2]:
                    st.text(f"Tags: {conn['tags']}")
                with cols[3]:
                    if st.button("Delete", key=f"delete_conn_{i}_{st.session_state.get('form_key', 0)}"):
                        delete_connection(conn['from'], conn['to'])
                        # Increment form key to reset form inputs
                        st.session_state['form_key'] = st.session_state.get('form_key', 0) + 1
                        # Force rerun to show the updated form
                        st.rerun()

    # Branch Creation (simplified for Phase I)
    if len(existing_units) >= 2:
        st.subheader("Create Branch")
        branch_from = st.selectbox("Branch From Unit", existing_units, key=f"branch_from_{st.session_state.get('form_key', 0)}")
        branch_to_count = st.number_input("Number of Branch Outputs", min_value=2, max_value=5, value=2, step=1, key=f"branch_to_count_{st.session_state.get('form_key', 0)}")
        
        branch_to_units = []
        branch_tags = []
        
        for i in range(branch_to_count):
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                to_unit = st.selectbox(f"To Unit {i+1}", existing_units, key=f"branch_to_{i}_{st.session_state.get('form_key', 0)}")
                branch_to_units.append(to_unit)
            with col_b2:
                tag = st.text_input(f"Tags {i+1}", key=f"branch_tag_{i}_{st.session_state.get('form_key', 0)}")
                branch_tags.append(tag)
        
        if st.button("Create Branch", key=f"create_branch_{st.session_state.get('form_key', 0)}"):
            # Convert tags to the format expected by create_branch_in_sfiles
            tags_list = []
            for tag in branch_tags:
                parsed_tags = [t.strip() for t in tag.split(",") if t.strip()]
                tags_list.append({"he": [], "col": parsed_tags, "signal": []})
                
            new_sfiles = create_branch_in_sfiles(st.session_state.sfiles_string, branch_from, branch_to_units, tags_list)
            st.session_state.sfiles_string = new_sfiles
            # Increment form key to reset form inputs
            st.session_state['form_key'] = st.session_state.get('form_key', 0) + 1
            # Force rerun to show the updated form
            st.rerun()

    # Join Creation (simplified for Phase I)
    if len(existing_units) >= 2:
        st.subheader("Create Join")
        join_to = st.selectbox("Join To Unit", existing_units, key=f"join_to_{st.session_state.get('form_key', 0)}")
        join_from_count = st.number_input("Number of Join Inputs", min_value=2, max_value=5, value=2, step=1, key=f"join_from_count_{st.session_state.get('form_key', 0)}")
        
        join_from_units = []
        join_tags = []
        
        for i in range(join_from_count):
            col_j1, col_j2 = st.columns(2)
            with col_j1:
                from_unit = st.selectbox(f"From Unit {i+1}", existing_units, key=f"join_from_{i}_{st.session_state.get('form_key', 0)}")
                join_from_units.append(from_unit)
            with col_j2:
                tag = st.text_input(f"Tags {i+1}", key=f"join_tag_{i}_{st.session_state.get('form_key', 0)}")
                join_tags.append(tag)
        
        if st.button("Create Join", key=f"create_join_{st.session_state.get('form_key', 0)}"):
            # Convert tags to the format expected by create_join_in_sfiles
            tags_list = []
            for tag in join_tags:
                parsed_tags = [t.strip() for t in tag.split(",") if t.strip()]
                tags_list.append({"he": [], "col": parsed_tags, "signal": []})
                
            new_sfiles = create_join_in_sfiles(st.session_state.sfiles_string, join_from_units, join_to, tags_list)
            st.session_state.sfiles_string = new_sfiles
            # Increment form key to reset form inputs
            st.session_state['form_key'] = st.session_state.get('form_key', 0) + 1
            # Force rerun to show the updated form
            st.rerun()

    # Cycle Creation (simplified for Phase I)
    if len(existing_units) >= 2:
        st.subheader("Create Recycle")
        recycle_from = st.selectbox("Recycle From Unit", existing_units, key=f"recycle_from_{st.session_state.get('form_key', 0)}")
        recycle_to = st.selectbox("Recycle To Unit", existing_units, key=f"recycle_to_{st.session_state.get('form_key', 0)}")
        recycle_tags = st.text_input("Recycle Tags (comma-separated)", key=f"recycle_tags_{st.session_state.get('form_key', 0)}")
        
        if st.button("Create Recycle", key=f"create_recycle_{st.session_state.get('form_key', 0)}"):
            if recycle_from != recycle_to:
                new_sfiles = create_cycle_in_sfiles(st.session_state.sfiles_string, recycle_from, recycle_to, recycle_tags)
                st.session_state.sfiles_string = new_sfiles
                # Increment form key to reset form inputs
                st.session_state['form_key'] = st.session_state.get('form_key', 0) + 1
                # Force rerun to show the updated form
                st.rerun()
            else:
                st.warning("From Unit and To Unit cannot be the same.")

with col2:
    # SFILES Output
    st.subheader("SFILES 2.0 String")
    st.text_area("SFILES Output", st.session_state.sfiles_string, height=100, key="sfiles_output", disabled=True)
    
    # Import/Export SFILES
    st.subheader("Import/Export SFILES")
    import_sfiles = st.text_area("Import SFILES", key=f"import_sfiles_{st.session_state.get('form_key', 0)}", height=100)
    col_imp1, col_imp2 = st.columns(2)
    with col_imp1:
        if st.button("Import", key=f"import_button_{st.session_state.get('form_key', 0)}"):
            if import_sfiles.strip():
                # Validate the SFILES string
                try:
                    fs = Flowsheet()
                    fs.create_from_sfiles(import_sfiles, overwrite_nx=True)
                    st.session_state.sfiles_string = import_sfiles
                    # Reset the import text area
                    st.session_state['form_key'] = st.session_state.get('form_key', 0) + 1
                    st.rerun()
                except Exception as e:
                    st.error(f"Invalid SFILES string: {str(e)}")
    with col_imp2:
        if st.button("Export to Text Area", key=f"export_button_{st.session_state.get('form_key', 0)}"):
            st.session_state.import_sfiles = st.session_state.sfiles_string
            st.rerun()
    
    # Visualization
    st.subheader("Flowsheet Visualization")
    if st.session_state.sfiles_string.strip():
        try:
            fig = render_flowsheet_graph(st.session_state.sfiles_string)
            st.pyplot(fig)
        except Exception as e:
            st.error(f"Error rendering flowsheet: {str(e)}")
    else:
        st.info("No flowsheet data yet. Add a unit to begin.")