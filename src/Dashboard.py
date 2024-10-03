import os
import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import pandas as pd
import plotly.express as px
from dash.dash_table import DataTable
import base64
from waitress import serve

# Load the sub-agencies data at the start
sub_agencies_path = './data/SubAgencies to Agencies.xlsx'
sub_agencies_df = pd.read_excel(sub_agencies_path, sheet_name=0)

# Initialize Dash application
app = dash.Dash(__name__)

# Generate a list of unique agencies and abbreviations for the dropdown
agency_options = [
    {'label': row['AGENCY'], 'value': row['AGENCY']} for _, row in sub_agencies_df.iterrows()
] + [
    {'label': row['ABBV'], 'value': row['ABBV']} for _, row in sub_agencies_df.iterrows()
]

app.layout = html.Div([
    html.H1("Agency Analysis"),

    # Container for the input and search button for license plates
    html.Div([
        dcc.Input(id='lp-input', type='text', placeholder='Enter License Plate', style={'marginRight': '10px'}),
        html.Button('Search LP', id='search-button', style={'backgroundColor': '#4CAF50', 'color': 'white'}),
    ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '20px'}),

    # Container for the agency dropdown and label button
    html.Div([
        dcc.Dropdown(
            id='search-agency-dropdown',
            options=agency_options,
            placeholder='Select ABBV or AGENCY',
            multi=True,  # Enable multi-select
            style={'width': '300px', 'marginRight': '10px'},  # Set a wider width for the dropdown
            clearable=True,  # Allow clearing selections
        ),
        html.Button("Select Agency", id='select-agency-button', style={
            'backgroundColor': '#008CBA',
            'color': 'white',
            'border': 'none',
            'padding': '10px 15px',
            'fontSize': '16px',
            'cursor': 'default'
        }),
    ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '20px'}),

    # Container for the file upload, placed to the right
    html.Div([
        dcc.Upload(
            id='upload-data',
            children=html.Button('Upload Coverage File', style={'backgroundColor': '#008CBA', 'color': 'white'}),
            multiple=False
        ),
    ], style={'display': 'flex', 'justifyContent': 'flex-end', 'marginBottom': '20px'}),

    dcc.Graph(id='heatmap'),
    DataTable(id='state-table'),
    dcc.Download(id='download'),
    html.Hr()
])

@app.callback(
    Output('heatmap', 'figure'),
    Output('state-table', 'data'),
    Input('upload-data', 'contents'),
    Input('lp-input', 'value'),
    Input('search-button', 'n_clicks'),
    Input('search-agency-dropdown', 'value'),  # Get selected values from the dropdown
    State('upload-data', 'filename')
)
def update_content(contents, lp_input, lp_n_clicks, selected_agencies, filename):
    # Check if any agencies were selected
    if selected_agencies:
        # Search for agencies
        agency_data = sub_agencies_df[
            sub_agencies_df['AGENCY'].isin(selected_agencies) | 
            sub_agencies_df['ABBV'].isin(selected_agencies)
        ]

        if not agency_data.empty:
            # Get the unique states for the found agencies
            states_covered = agency_data['Agency STATE'].unique()
            state_counts = pd.DataFrame({'agency state': states_covered, 'Count': [1] * len(states_covered)})

            fig = px.choropleth(
                state_counts,
                locations="agency state",
                locationmode="USA-states",
                color="Count",
                scope="usa",
                title=f"Heatmap for Agencies: {', '.join(selected_agencies)}",
                color_continuous_scale="YlOrRd",
                hover_name="agency state",
                hover_data={"Count": True}
            )

            return fig, agency_data.to_dict('records')
        else:
            return px.choropleth(locations=[], scope="usa", title="No data found for the selected agencies"), []

    # Check if the LP search button was clicked
    if contents is not None and lp_n_clicks:
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)

        # Read the main coverage data
        df = pd.read_excel(decoded, sheet_name=0)

        if filename == 'Coverage Lps.xlsx':
            file_type = 'primary'
        elif filename == 'updated_agency.xlsx':
            file_type = 'alternative'
        else:
            return px.choropleth(locations=[], scope="usa", title="Invalid file"), []

        if lp_input:
            lp_input = lp_input.upper()

            if file_type == 'primary':
                # Handling for 'Coverage Lps.xlsx'
                filtered_data = df[df['license plate'] == lp_input]
                if not filtered_data.empty:
                    # Merge with sub-agencies data
                    merged_data = pd.merge(
                        filtered_data,
                        sub_agencies_df,
                        how='left',
                        left_on='agency name',  # Adjust this key as per your actual data
                        right_on='AGENCY'
                    )

                    # Confirm agency state matches
                    merged_data = merged_data[merged_data['agency state'] == merged_data['Agency STATE']]

                    # Group and aggregate the data
                    merged_data = merged_data.groupby('license plate').agg({
                        'agency state': lambda x: ', '.join(x.unique()),
                        'exists in aap': lambda x: True if (x == 1).any() else False,
                        'was in aap': lambda x: True if (x == 1).any() else False,
                        'agency name': lambda x: ', '.join(x.unique()),
                        'lifecycle state': lambda x: ', '.join(x.unique()), 
                        'abbreviation': lambda x: ', '.join(x.unique()),
                        'Accounts_In_LP_Magement': lambda x: ', '.join(x.unique()),
                        'AGENCY RECOMMENDED ACCOUNT': lambda x: ', '.join(x.unique())  # Using the new column
                    }).reset_index()

                    merged_data.rename(columns={'abbreviation': 'LP State'}, inplace=True)

                    states_covered = merged_data['agency state'].iloc[0].split(', ')
                    plate_state_counts = pd.DataFrame({'agency state': states_covered, 'Count': [1] * len(states_covered)})

                    fig = px.choropleth(
                        plate_state_counts,
                        locations="agency state",
                        locationmode="USA-states",
                        color="Count",
                        scope="usa",
                        title=f"Heatmap for License Plate: {lp_input}",
                        color_continuous_scale="YlOrRd",
                        hover_name="agency state",
                        hover_data={"Count": True}
                    )

                    recommendations_table = merged_data.to_dict('records')
                    return fig, recommendations_table
                else:
                    return px.choropleth(
                        locations=[],
                        scope="usa",
                        title=f"No data found for License Plate: {lp_input}"
                    ), []
            else:
                filtered_data = df[df['license_plate'] == lp_input]
                if not filtered_data.empty:
                    # Similar handling as above for the alternative file
                    merged_data = pd.merge(
                        filtered_data,
                        sub_agencies_df,
                        how='left',
                        left_on='agency name',  # Adjust this key as per your actual data
                        right_on='AGENCY'
                    )

                    # Confirm agency state matches
                    merged_data = merged_data[merged_data['agency state'] == merged_data['Agency STATE']]

                    merged_data = merged_data.groupby('license_plate').agg({
                        'STATE_GOOGLE': lambda x: ', '.join(x.unique()),
                        'agency name': lambda x: ', '.join(x.unique()),
                        'lifecycle state': lambda x: ', '.join(x.unique()), 
                        'abbreviation': lambda x: ', '.join(x.unique()),
                        'exists in aap': lambda x: True if (x == 1).any() else False,
                        'was in aap': lambda x: True if (x == 1).any() else False,
                        'Accounts_In_LP_Magement': lambda x: ', '.join(x.unique()),
                        'AGENCY RECOMMENDED ACCOUNT': lambda x: ', '.join(x.unique())  # Using the new column
                    }).reset_index()

                    merged_data.rename(columns={'STATE_GOOGLE': 'agency state'}, inplace=True)

                    states_covered = merged_data['agency state'].iloc[0].split(', ')
                    plate_state_counts = pd.DataFrame({'agency state': states_covered, 'Count': [1] * len(states_covered)})

                    fig = px.choropleth(
                        plate_state_counts,
                        locations="agency state",
                        locationmode="USA-states",
                        color="Count",
                        scope="usa",
                        title=f"Heatmap for License Plate: {lp_input}",
                        color_continuous_scale="YlOrRd",
                        hover_name="agency state",
                        hover_data={"Count": True}
                    )

                    recommendations_table = merged_data.to_dict('records')
                    return fig, recommendations_table
                else:
                    return px.choropleth(
                        locations=[],
                        scope="usa",
                        title=f"No data found for License Plate: {lp_input}"
                    ), []
    return px.choropleth(locations=[], scope="usa", title="No search input"), []

# Starting the server
if __name__ == '__main__':
    serve(app.server, host='0.0.0.0', port=8050)
