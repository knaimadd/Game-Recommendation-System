from dash import Dash, html, dcc, Input, Output, State
import dash_bootstrap_components as dbc
import requests


from UserEmbedding import UserEmbedding, get_app_url


STEAM_API_KEY = "XXX"
app = Dash(__name__, external_stylesheets=[dbc.themes.DARKLY])
server = app.server

# ===== LAYOUT =====
app.layout = dbc.Container([
    html.H1([
    html.Span("✦ ", style={"color": "#66c0f4"}),
    "Steam Games Recommender",
    html.Span(" ✦", style={"color": "#66c0f4"})
], className="my-6 text-center h1-title-text"),

    dbc.Row([
        dbc.Col(
            dcc.Dropdown(
                id="profile-type",
                options=[
                    
                    {"label": "id/", "value": "id"},
                    {"label": "profiles/", "value": "profiles"}
                ],
                value="id",
                clearable=False,
                className="steam-dropdown",
                style={"width": "100%"}
            ),
            width=2
        ),
        dbc.Col(
            dcc.Input(
                id="profile-value",
                type="text",
                placeholder="Enter Steam ID or username",
                style={"width": "100%"},
                className="steam-input"
            ),
            width=7
        ),
        dbc.Col(
            dbc.Button(
                "Recommendations ⯈",
                id="submit-btn",
                color="primary",
                className="w-100"
            ),
            width=3
        )
    ], className="mb-4 g-2"),

    dcc.Loading(
        html.Div(id="results"),
        type="circle"
    )
], fluid=True)


def get_image_url(appid):
    library_url = f"https://steamcdn-a.akamaihd.net/steam/apps/{appid}/library_600x900_2x.jpg"
    fallback_url = f"https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/{appid}/header.jpg"
    
    try:
        r = requests.head(library_url, timeout=2)
        if r.status_code == 200:
            return library_url, False
        else:
            return fallback_url, True
    except:
        return fallback_url, True

@app.callback(
    Output("results", "children"),
    Input("submit-btn", "n_clicks"),
    State("profile-type", "value"),
    State("profile-value", "value"),
    prevent_initial_call=True
)

def generate_recommendations(n_clicks, profile_type, profile_value):
    if not profile_value:
        return dbc.Alert("Please enter a valid Steam profile identifier.", color="warning")

    profile_url = f"https://steamcommunity.com/{profile_type}/{profile_value}/"

    try:
        user = UserEmbedding(profile_url, STEAM_API_KEY)
        user.build_user_vector()
        recs = user.recommend_games(10)

        if not recs:
            return dbc.Alert("No recommendations could be generated.", color="warning")

    except Exception as e:
        return dbc.Alert(str(e), color="danger")

    cards = []
    for idx, (name, score, appid) in enumerate(recs):
        img_url, is_fallback = get_image_url(appid)
        container_class = "game-cover-container fallback" if is_fallback else "game-cover-container"

        cards.append(
            dbc.Col(
                dbc.Card(
                    [
                        html.Div(
                            [html.Img(
                                src=img_url,
                            ),
                            html.Div(f"#{idx+1}", className="game-rank")],
                            className=container_class
                        ),
                        dbc.CardBody(
                            [
                                html.H6(name, className="fw-bold text-truncate", title=name),
                                dbc.Button(
                                    "View on Steam",
                                    href=get_app_url(appid),
                                    target="_blank",
                                    color="primary",
                                    size="sm",
                                    className="mt-2 w-100"
                                )
                            ]
                        )
                    ],
                    className="h-100 shadow-sm",
                    style={"borderRadius": "12px"}
                ),
                width=2
            )
        )


    return html.Div([
        html.H3(f"Recommendations for {user.username}", className="mb-3"),
        dbc.Row(cards, className="g-4")
    ])


if __name__ == "__main__":
    app.run(debug=False)
