import dash
from dash import dcc
from dash import html
from dash.dependencies import Input, Output, State
import dash_bootstrap_components as dbc
import pandas as pd
from dash import dash_table
import os
from sqlalchemy import create_engine
from saagieapi import SaagieApi

# Environment variables
postgresql_host = os.environ["POSTGRESQL_HOST"]
postgresql_port = os.environ["POSTGRESQL_PORT"]
postgresql_user = os.environ["POSTGRESQL_ADMIN_LOGIN"]
postgresql_pwd = os.environ["POSTGRESQL_ADMIN_PWD"]
postgresql_db = os.environ["POSTGRESQL_DATABASE_NAME"]

text_color = '#263D5C'
text_color2 = '#587193'
btn_color = "primary"
border_color = "#D9DBE3"
border_radius = 6
btn_style = {"height": 40, "width": 100, "border-radius": border_radius}


app = dash.Dash(__name__, external_stylesheets=[dbc.themes.LUX], url_base_pathname=os.environ["SAAGIE_BASE_PATH"]+"/")

postgresql_string_connecion = f'postgresql://{postgresql_user}:{postgresql_pwd}@{postgresql_host}:{postgresql_port}/{postgresql_db}?sslmode=require'
pg_engine = create_engine(postgresql_string_connecion)

saagie_client = SaagieApi(url_saagie=os.environ["SAAGIE_URL"],
                          id_platform=os.environ["SAAGIE_PLATFORM_ID"],
                          user=os.environ["SAAGIE_LOGIN"],
                          password=os.environ["SAAGIE_PWD"],
                          realm=os.environ["SAAGIE_REALM"])

list_projects = saagie_client.projects.list()
if list_projects and "projects" in list_projects:
    projects = list_projects["projects"]
    projects_name = [project["name"] for project in projects]
    projects_pipelines = [{project["name"]: saagie_client.pipelines.list_for_project_minimal(project["id"])["project"]["pipelines"]} for project in list_projects["projects"] ]
    projects_id = [{project["name"]: project["id"]} for project in projects]
else:
    projects_name = ["No project found"]


@app.callback(
    Output(component_id='pipelines', component_property='options'),
    Input(component_id="project-dropdown", component_property="value")
)
def update_pipelines(value):
    pipelines_name = []
    pipelines = [project_pipeline[value] for project_pipeline in projects_pipelines if project_pipeline.get(value)]
    if pipelines:
        pipelines_name = [pipeline["name"] for pipeline in pipelines[0]]
    return pipelines_name

@app.callback(
    Output(component_id='output-execution', component_property='children'),
    Input(component_id='submit-button-state', component_property='n_clicks'),
    State(component_id="nb-pipeline", component_property="value"),
    State(component_id="project-dropdown", component_property="value"),
    State(component_id='pipelines', component_property='value'),
    State(component_id="env-vars-tube-name", component_property="value"),
    State(component_id="env-vars-diameter", component_property="value"),
    State(component_id="env-vars-options", component_property="value"),
)
def run_piepline(n_clicks, nb_pipelines, project_name, pipeline_name, tube_name, diameter, options):
    changed_ids = [p['prop_id'].split('.')[0] for p in dash.callback_context.triggered]
    button_pressed = 'submit-button-state' in changed_ids
    json_data = {}
    if button_pressed:
        pipeline_id = saagie_client.pipelines.get_id(pipeline_name=pipeline_name, project_name=project_name)
        if tube_name:
            json_data = {"tube_name": tube_name, "diameter": diameter}
            if options:
                json_data["options"] = options
            saagie_client.env_vars.bulk_create_for_pipeline(pipeline_id, json_data)
        list_pipeline_status = []

        for i in range(int(nb_pipelines)):
            if (int(nb_pipelines) > 1) & (i > 0):
                json_data["diameter"] = float(diameter) + i
                saagie_client.env_vars.bulk_create_for_pipeline(pipeline_id, json_data)
            status = saagie_client.pipelines.run_with_callback(pipeline_id=pipeline_id)
            list_pipeline_status.append(status)

        return f"Successfully execute {nb_pipelines} times the pipeline '{pipeline_name}' in the project '{project_name}'"
    else:
        return ""


@app.callback(Output('postgresql_table', 'children'),
              [Input('refresh', 'n_clicks')])
def populate_datatable(refresh):
    df = pd.read_sql(f'SELECT * FROM  tb_tube', pg_engine)
    dt = dash_table.DataTable(df.to_dict('records'),
                              [{"name": i, "id": i} for i in df.columns],
                              cell_selectable=True,
                              style_cell={'textAlign': 'center'},
                              sort_action='native',
                              filter_action='native',
                              page_size=5,)
    return dt


app.layout = dbc.Container(children=[
    dbc.Tooltip(
        "Name of the tube, should be a text ",
        target="env-vars-tube-name",
    ),
    dbc.Tooltip(
        "Diameter of the tube, should be a number ",
        target="env-vars-diameter",
    ),
    dbc.Tooltip(
        "Number of execution of pipeline. "
        "If number > 1, then diameter will be incremented by 1 in each execution",
        target="nb-pipeline",
    ),
    dbc.Row([
        dbc.Col([dbc.Row(
            html.H2("Saagie Pipeline APP"),
            style={"offset": 1, 'color': text_color, 'margin-top': '30px'},
            justify="left")
        ]),
        dbc.Col([
            dbc.Row(dbc.Button("⟳ Refresh", id="refresh", n_clicks=0, size='sm', href='/',
                               style={"height": 30, "width": 100, "font-size": 12,
                                      "color": "#132d81", "background-color": "White", 'margin-top': '30px'})
                    , justify="center"),
        ], width=2),

    ],
        style={'color': text_color}),
    # Description
    dbc.Row(
        [
            html.H6("A interface that user can use to execute Saagie pipelines")
        ],
        style={"offset": 1, 'color': text_color2},
        justify="left",
    ),
    dbc.Row(html.Br(), class_name=".mb-4"),

    # Main part
    dbc.Row(
        [
            # Left
            dbc.Col([
                html.P('Saagie Project'),
                dcc.Dropdown(projects_name,
                             id="project-dropdown",
                             style={'height': '20%'},
                             ),
                html.P('Saagie Pipeline'),
                dcc.Dropdown(id="pipelines", style={'height': '20%'}),
                html.P('Number of execution of pipelines'),
                dcc.Input(id="nb-pipeline", value='1', type='number', min=1, step=1, required=True,
                          style={'height': '10%', 'width': '100%'}),
            ],
                style={"offset": 1, 'margin-top': '40px', 'color': text_color, "border-right": "1px solid #d9dbe3"},
            ),

            # Right
            dbc.Col([
                html.P("Environment variables of pipelines"),
                html.P('Tube name: '),
                dcc.Input(id="env-vars-tube-name", type='text',
                          placeholder="Type some text...", required=True, style={'height': '10%', 'width': '100%'}),
                dbc.Row(html.Br(), class_name=".mb-4"),
                html.P('Diameter (cm): '),
                dcc.Input(id="env-vars-diameter", type='number',
                          placeholder="Type some number...", min=1, required=True, style={'height': '10%', 'width': '100%'}),
                dbc.Row(html.Br(), class_name=".mb-4"),

                html.P('Options: '),
                dbc.Select(
                    id="env-vars-options",
                    options=[
                        {"label": "Option 1", "value": "1"},
                        {"label": "Option 2", "value": "2"},
                        {"label": "Disabled option", "value": "3", "disabled": True},
                    ],
                    style={'height': '10%', 'width': '100%'}
                ),
                dbc.Row(html.Br()),
                dbc.Row(dbc.Button("Run", id="submit-button-state", n_clicks=0, className="col-6 mx-auto",
                                   color="success",
                                   style={"verticalAlign": "middle"}
                                   )
                        , justify="center"
                        ),

            ],
                style={'color': text_color}
            )

        ]),
    dbc.Row(html.Br(), class_name=".mb-4"),
    dbc.Row(
        dbc.Col(
            dcc.Markdown(id="output-execution"),
        ),
        style={"offset": 1, 'color': text_color2},
        justify="left",
    ),
    dbc.Row(html.Br(), class_name=".mb-4"),
    dbc.Row(id="postgresql_table"),
    dbc.Row(html.Br(), class_name=".mb-4"),


], style={"font-family": "Arial", "font-size": "12", "font-weight": "bold"})

if __name__ == '__main__':
    app.run_server(host='0.0.0.0', debug=True, port=8050)
