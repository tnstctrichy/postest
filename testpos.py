import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from io import BytesIO
import os

# Streamlit configuration
st.set_page_config(
    page_title="POS Dashboard - T.N.S.T.C. Trichy Region",
    layout="wide",
    page_icon="🚌"  # Example icon
)

# Get yesterday's date
yesterday_date = (datetime.now() - timedelta(days=1)).strftime("%d-%m-%Y")

# Enhanced title with styling and border
st.markdown(f"""
    <div style="border: 4px solid #4CAF50; padding: 15px; border-radius: 15px; background-color: #E3F2FD; text-align: center;">
        <h1 style="color: #FF5722; font-family: 'Segoe UI', sans-serif; font-size: 45px; margin-bottom: 5px;">
            POS Dashboard - T.N.S.T.C. Trichy Region
        </h1>
        <h2 style="color: #4CAF50; font-family: 'Arial', sans-serif; font-size: 36px; margin-bottom: 0;">
            Data as of {yesterday_date}
        </h2>
    </div>
    """, unsafe_allow_html=True)

# Sidebar for navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio("Choose an option", ["View Dashboard", "Upload Data"])

# Initialize session state for uploaded data
if "uploaded_data" not in st.session_state:
    st.session_state.uploaded_data = None
if "file_name" not in st.session_state:
    st.session_state.file_name = None

# Define the folder where files will be saved
UPLOAD_FOLDER = "uploaded_files"

# Ensure the folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Password-protected upload section
if page == "Upload Data":
    if "upload_authenticated" not in st.session_state:
        st.session_state.upload_authenticated = False

    if not st.session_state.upload_authenticated:
        password = st.text_input("Enter the admin password for upload:", type="password")
        if password == "admin123":
            st.session_state.upload_authenticated = True
            st.success("Password correct! You can now upload data.")
        else:
            st.stop()

    st.markdown("### Upload POS Excel File")
    uploaded_file = st.file_uploader("Upload Excel File", type=["xlsx"])

    if uploaded_file:
        try:
            data = pd.read_excel(uploaded_file)
            required_columns = ["SNO", "BRANCH", "RTNO", "VHNO", "ROUTE", "TYPE", "OPKM", "COLLECT", "EPKM", "REMARKS"]

            # Validate columns
            if all(col in data.columns for col in required_columns):
                st.session_state.uploaded_data = data
                st.session_state.file_name = uploaded_file.name

                # Save the uploaded file locally
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                file_path = os.path.join(UPLOAD_FOLDER, f"uploaded_data_{timestamp}.xlsx")
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                st.success(f"File '{uploaded_file.name}' uploaded and saved successfully!")

                # Provide a download link for the uploaded file
                st.markdown(f"[Download the uploaded file](/{UPLOAD_FOLDER}/{file_path.split('/')[-1]})")
            else:
                st.error(f"The file must contain the required columns: {', '.join(required_columns)}")
        except Exception as e:
            st.error(f"Error processing the file: {e}")

# View Dashboard (Default Page)
if page == "View Dashboard":
    if st.session_state.uploaded_data is None:
        st.warning("No data uploaded yet. Please upload an Excel file in the 'Upload Data' section.")
    else:
        st.markdown(f"### Currently Displaying Data from: `{st.session_state.file_name}`")

        # Prepare data
        data = st.session_state.uploaded_data.copy()
        data = data.drop(columns=["SNO"], errors="ignore")  # Remove record ID column
        data["OPKM"] = data["OPKM"].astype(int)  # Ensure OPKM is a whole number
        data["EPKM"] = data["EPKM"].round(2)  # Format EPKM to 2 decimal places
        data.index += 1  # Reset index starting from 1

        # Highlight EPKM values below threshold
        def highlight_blink(val):
            if isinstance(val, (int, float)) and val < 30.00:
                return "background-color: yellow; color: red; font-weight: bold; animation: blink 1.5s infinite;"
            return ""

        # POS Data Dashboard
        st.markdown("### POS Data Dashboard")
        st.dataframe(
            data.style.applymap(highlight_blink, subset=["EPKM"])
            .set_table_styles(
                [{"selector": "thead th", "props": [("font-size", "18px"), ("color", "white"), ("background-color", "#4CAF50")]}]
            ),
            height=600,
        )

        # Threshold Settings
        st.sidebar.markdown("### Threshold Settings")
        epkm_threshold = st.sidebar.number_input("Set Threshold EPKM", value=30, step=1)

        # Vehicles Below Threshold
        below_threshold = data[data["EPKM"] < epkm_threshold]
        below_threshold = below_threshold.reset_index(drop=True)
        below_threshold.index += 1  # Reset index starting from 1

        st.markdown(f"### Vehicles Below EPKM Threshold (Rs. {epkm_threshold:.2f})")
        if not below_threshold.empty:
            st.dataframe(
                below_threshold.style.applymap(highlight_blink, subset=["EPKM"])
                .set_table_styles(
                    [{"selector": "thead th", "props": [("font-size", "18px"), ("color", "white"), ("background-color", "#4CAF50")]}]
                ),
                height=500,
            )
        else:
            st.success(f"All vehicles have EPKM above Rs. {epkm_threshold:.2f}!")

        # Download Option for Filtered Data
        st.sidebar.markdown("### Download Filtered Data")
        if not below_threshold.empty:
            buffer = BytesIO()
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                below_threshold.to_excel(writer, index=False, sheet_name="Below Threshold")
            buffer.seek(0)

            st.sidebar.download_button(
                label="Download Below Threshold Data (Excel)",
                data=buffer,
                file_name=f"below_threshold_{epkm_threshold}_epkm.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.sidebar.info("No data to download.")

        # EPKM Distribution Visualization
        st.markdown("### EPKM Distribution Across Branches and Routes")
        
        # Branch-wise Aggregation with Threshold
        branch_summary = data[data["EPKM"] < epkm_threshold].groupby("BRANCH")["RTNO"].count().reset_index()
        branch_summary.rename(columns={"RTNO": "Route Count"}, inplace=True)
        
        fig_branch = px.bar(branch_summary, x="BRANCH", y="Route Count", color="BRANCH",
                            title="Route Count by Branch (Below Threshold)",
                            labels={"BRANCH": "Branch", "Route Count": "Number of Routes"},
                            color_discrete_sequence=px.colors.qualitative.Set1)
        st.plotly_chart(fig_branch, use_container_width=True)

        # Route-wise Visualization with Threshold
        route_summary = data[data["EPKM"] < epkm_threshold]
        fig_route = px.bar(route_summary, x="RTNO", y="EPKM", color="RTNO",
                           title="EPKM by Route Code (Below Threshold)",
                           labels={"RTNO": "Route Code", "EPKM": "EPKM (Rs.)"},
                           color_discrete_sequence=px.colors.qualitative.Set2)
        st.plotly_chart(fig_route, use_container_width=True)

        # Search Filters
        st.sidebar.markdown("### Search Filters")
        search_route = st.sidebar.text_input("Search by Route Code or Route Name")
        search_branch = st.sidebar.text_input("Search by Branch")

        if search_route or search_branch:
            filtered_data = data[(
                data["RTNO"].astype(str).str.contains(search_route, case=False, na=False) if search_route else True) &
                (data["BRANCH"].astype(str).str.contains(search_branch, case=False, na=False) if search_branch else True)
            ]
            st.markdown(f"### Search Results for Route '{search_route}' and Branch '{search_branch}'")
            st.dataframe(filtered_data)

# Add CSS for blinking effect
st.markdown("""
    <style>
    @keyframes blink {
        50% { opacity: 0; }
    }
    </style>
    """, unsafe_allow_html=True)
