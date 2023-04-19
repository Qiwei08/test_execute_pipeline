import dash
from dash import dcc
from dash import html
from dash.dependencies import Input, Output, State
import dash_bootstrap_components as dbc
import os
from saagieapi import SaagieApi
import json
from gql import gql
import logging


external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

markdown_text = '''
### Launch Saagie Pipeline APP

Please make sure that you have set the following environment variables and make sure that your SAAGIE_LOGIN have access
to project that you want to launch pipeline:
- SAAGIE_URL
- SAAGIE_PLATFORM_ID
- SAAGIE_LOGIN
- SAAGIE_PWD
- SAAGIE_REALM

'''

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.LUX], url_base_pathname=os.environ["SAAGIE_BASE_PATH"]+"/")


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
            if (int(nb_pipelines) > 1) & (i > 1):
                json_data["diameter"] = float(diameter) + i
                saagie_client.env_vars.bulk_create_for_pipeline(pipeline_id, json_data)
            status = saagie_client.pipelines.run_with_callback(pipeline_id=pipeline_id)
            list_pipeline_status.append(status)

        return f"Successfully execute {nb_pipelines} times the pipeline '{pipeline_name}' in the project '{project_name}'"
    else:
        return ""


app.layout = html.Div([
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
    dbc.Row(
        dbc.Col(
            dcc.Markdown(children=markdown_text),
            style={"padding": 10}
        )
    ),
    dbc.Row(
        [
            dbc.Col(
                [
                    html.Label('Saagie Project'),
                    dcc.Dropdown(projects_name,
                                 id="project-dropdown"
                                 )
                ],
                width={"offset": 1}
            ),
            dbc.Col(html.P("Environment variables of pipelines"))
        ],
        justify="center",
    ),

    dbc.Row(
        [
            dbc.Col(
                [
                    html.Label('Saagie Pipeline'),
                    dcc.Dropdown(id="pipelines"),
                ],
                width={"offset": 1}
            ),
            dbc.Col(
                [
                    html.Label('Tube name: '),
                    dcc.Input(id="env-vars-tube-name", type='text',
                              placeholder="Type some text...", required=True)
                ]
            )
        ],
        justify="center",
    ),

    dbc.Row(
        [
            dbc.Col(
                [
                    html.P('Number of execution of pipelines'),
                    dcc.Input(id="nb-pipeline", value='1', type='number', min=1, step=1, required=True)
                ],
                width={"offset": 1}
            ),
            dbc.Col(
                [
                    html.Label('Diameter (cm): '),
                    dcc.Input(id="env-vars-diameter", type='number',
                              placeholder="Type some number...", min=1, required=True),
                    dbc.Row(html.Br()),
                    dbc.Label('Options: '),
                    dbc.Select(
                        id="env-vars-options",
                        options=[
                            {"label": "Option 1", "value": "1"},
                            {"label": "Option 2", "value": "2"},
                            {"label": "Disabled option", "value": "3", "disabled": True},
                        ],
                    ),
                    dbc.Row(html.Br()),
                    dbc.Button('Refresh Data', href='/', className="me-1"),
                    dbc.Button(id='submit-button-state', n_clicks=0, children='Submit', className="me-1"),

                ]
            )
        ],
        justify="center",
    ),
    dbc.Row(
        dbc.Col(
            dcc.Markdown(id="output-execution"),
            style={"padding": 10}
        )
    ),

], style={"font-family": "Arial", "font-size": "0.9em", "text-align": "center"})

if __name__ == '__main__':
    app.run_server(host='0.0.0.0', debug=True, port=8050)
