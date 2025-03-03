# SFILES 2.0 Flowsheet Builder

## Overview

This is a Phase I implementation of a GUI for creating flowsheets using the SFILES 2.0 notation. It allows wastewater engineers and other users to build chemical process flowsheets step by step without needing to know the SFILES 2.0 notation directly.

## Features

- Add units to the flowsheet
- Connect units with streams
- Create branches (multiple outputs from one unit)
- Create joins (multiple inputs to one unit)
- Create recycles (cycles in the flowsheet)
- Import/Export SFILES 2.0 strings
- Real-time visualization of the flowsheet

## Installation

### Prerequisites

- Python 3.9+
- Streamlit
- NetworkX
- Matplotlib

### Setup

1. Clone or download this repository
2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage

1. Navigate to the repository directory
2. Run the Streamlit app:
   ```
   streamlit run flowsheet_builder.py
   ```
3. Open your web browser and go to `http://localhost:8501`