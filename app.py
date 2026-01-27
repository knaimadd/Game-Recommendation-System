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
            dcc.Input(
                id="profile-url",
                type="text",
                placeholder="Enter full Steam profile URL (e.g. https://steamcommunity.com/id/username/)",
                style={"width": "100%"},
                className="steam-input"
            ),
            width=7
        ),
        dbc.Col(
            dcc.Input(
                id="n-games",
                type="int",
                placeholder="Number of games e.g. 10",
                style={"width": "100%"},
                className="steam-input"
            ),
            width=2
        ),
        dbc.Col(
            dbc.Button(
                "Get Recommendations",
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
    Input("profile-url", "n_submit"),
    Input("n-games", "n_submit"),
    State("profile-url", "value"),
    State("n-games", "value"),
    prevent_initial_call=True
)

def generate_recommendations(n_clicks, profile_url_enter, n_games_enter, profile_url, n_games):
    if not profile_url:
        return dbc.Alert("Please enter a valid Steam profile URL.", color="warning")

    profile_url = profile_url.strip()
    if not (profile_url.startswith("http://") or profile_url.startswith("https://")):
        return dbc.Alert("Please enter a full URL starting with http:// or https://", color="warning")
    if not profile_url.endswith("/"):
        profile_url += "/"

    try:
        n_games = int(n_games) if n_games else 10
        if n_games <= 0:
            n_games = 10
    except Exception:
        n_games = 10

    try:
        user = UserEmbedding(profile_url, STEAM_API_KEY)
        user.build_user_vector()
        recs = user.recommend_games(n_games)

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
        dbc.Row(cards, className="g-4", justify="center")
    ])


if __name__ == "__main__":
    app.run(debug=False)
