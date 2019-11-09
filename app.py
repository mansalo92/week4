import pandas as pd
import dash
import dash_core_components as dcc
import dash_html_components as html
import plotly.graph_objects as go
import dash_table

from sqlalchemy import create_engine

engine = create_engine('postgresql://postgres:violista92@dsa.cqdpo7wibptj.us-east-2.rds.amazonaws.com/extended_4')
df = pd.read_sql("SELECT * from aggr", engine.connect(), parse_dates=('OCCURRED_ON_DATE',))

#df = pd.read_csv('aggr.csv', parse_dates=['Entry time'])

token='pk.eyJ1IjoibWFuc2FsbzkyIiwiYSI6ImNrMmhwcXQ4aDE4Y3QzY3RnaWJkeHFwZWYifQ.SwjwUBtHACf_b2J5FFRmog'

app = dash.Dash(__name__, external_stylesheets=['https://codepen.io/uditagarwal/pen/oNvwKNP.css', 'https://codepen.io/uditagarwal/pen/YzKbqyV.css'])


app.layout = html.Div(children=[
    html.Div(children=[ html.H2(children="Bitcoin Leveraged Trading Backtest Analysis", className='h2-title'),],
            className='study-browser-banner row'),
    html.Div(className="row app-body",children=[html.Div(className="twelve columns card",
                children=[html.Div(className="padding row",children=[
                            html.Div(className="two columns card",children=[
            html.H6("Select Exchange",),dcc.RadioItems(id="exchange-select",
                                        options=[{'label': label, 'value': label} for label in df['Exchange'].unique()],
                                        value='Bitmex',
                                        labelStyle={'display': 'inline-block'})]),html.Div(className="two columns card",children=[
            html.H6("Select Leverage",),dcc.RadioItems(id="leverage-select",
                                        options=[{'label': label, 'value': label} for label in df['Margin'].unique()],
                                        value='1',
                                        labelStyle={'display': 'inline-block'})]),html.Div(className="three columns card",children=[
            html.H6("Select Data Range",),dcc.DatePickerRange(id="date-range", display_format="MMM YY",
                                        start_date=df['Entry time'].min(),
                                        end_date=df['Entry time'].max())]),
                                    html.Div(id="strat-returns-div",
                                className="two columns indicator pretty_container",
                                children=[
                                    html.P(id="strat-returns", className="indicator_value"),
                                    html.P('Strategy Returns', className="twelve columns indicator_text"),]),
                                    html.Div(
                                id="market-returns-div",
                                className="two columns indicator pretty_container",
                                children=[
                                    html.P(id="market-returns", className="indicator_value"),
                                    html.P('Market Returns', className="twelve columns indicator_text"),]), 
                                    html.Div(id="strat-vs-market-div",
                                className="two columns indicator pretty_container",
                                children=[
                                    html.P(id="strat-vs-market", className="indicator_value"),
                                    html.P('Strategy vs. Market Returns', className="twelve columns indicator_text"),]),])]),                                             html.Div(className="twelve columns card",
                                children=[dcc.Graph(id="monthly-chart",
                                    figure={'data': []})]),
                                    html.Div(className="padding row",
                                children=[
                                    html.Div(className="six columns card",
                                children=[
                            dash_table.DataTable(id='table',
                                columns=[
                                    {'name': 'Number', 'id': 'Number'},
                                    {'name': 'Trade type', 'id': 'Trade type'},
                                    {'name': 'Exposure', 'id': 'Exposure'},
                                    {'name': 'Entry balance', 'id': 'Entry balance'},
                                    {'name': 'Exit balance', 'id': 'Exit balance'},
                                    {'name': 'Pnl (incl fees)', 'id': 'Pnl (incl fees)'},],
                                style_cell={'width': '50px'},
                                style_table={
                                    'maxHeight': '450px',
                                    'overflowY': 'scroll'},)]),
                                    dcc.Graph(id="pnl-types",
                                    className="six columns card",figure={})]),
                                    html.Div(className="padding row",
                                children=[
                                    dcc.Graph(id="daily-btc",
                                    className="six columns card",
                                    figure={}), dcc.Graph(id="balance",
                                    className="six columns card",
                                    figure={})])])])

#Helper Function filter_df
    
def filter_df(df,exchange, margin, start_date, end_date):
    exc = (df['Exchange'] == exchange)
    marg = (df['Margin'] == int(margin))
    rang = ((df['Entry time'] > start_date) & (df['Entry time'] <= end_date))
    return df[(exc & marg & marg)]
                                                         

#Callback for uptdating date range by exchange select

@app.callback(
    [
        dash.dependencies.Output('date-range', 'start_date'),
        dash.dependencies.Output('date-range', 'end_date'),
    ],
    (
        dash.dependencies.Input('exchange-select', 'value'),
    ))
def update_range(value):
    df2 = df[df['Exchange']==value]
    return df2['Entry time'].min(),df2['Entry time'].max()
    
#Helper Functions to calculate the monthly returns of our strategy and create the candlestick chart

def calc_returns_over_month(df):
    out = []
    df['YearMonth']= df['Entry time'].dt.year.astype(str) + '-' + df['Entry time'].dt.month.astype(str)
    for name, group in df.groupby('YearMonth'):
        exit_balance = group.head(1)['Exit balance'].values[0]
        entry_balance = group.tail(1)['Entry balance'].values[0]
        monthly_return = (exit_balance*100 / entry_balance)-100
        out.append({
            'month': name,
            'entry': entry_balance,
            'exit': exit_balance,
            'monthly_return': monthly_return})
    return out


def calc_btc_returns(df):
    btc_start_value = df.tail(1)['BTC Price'].values[0]
    btc_end_value = df.head(1)['BTC Price'].values[0]
    btc_returns = (btc_end_value * 100/ btc_start_value)-100
    return btc_returns

def calc_strat_returns(df):
    start_value = df.tail(1)['Exit balance'].values[0]
    end_value = df.head(1)['Entry balance'].values[0]
    returns = (end_value * 100/ start_value)-100
    return returns

#Callback to calculate the monthly returns of our strategy and create the candlestick chart

@app.callback(
        dash.dependencies.Output('monthly-chart', 'figure'),
       (dash.dependencies.Input('exchange-select', 'value'),
        dash.dependencies.Input('leverage-select', 'value'),
        dash.dependencies.Input('date-range', 'start_date'),
        dash.dependencies.Input('date-range', 'end_date'),))

def update_monthly(exchange, leverage, start_date, end_date):
    dff = filter_df(df, exchange, leverage, start_date, end_date)
    data = calc_returns_over_month(dff)
    btc_returns = calc_btc_returns(dff)
    strat_returns = calc_strat_returns(dff)
    strat_vs_market = strat_returns - btc_returns

    return {'data': [go.Candlestick(open=[each['entry'] for each in data],
                     close=[each['exit'] for each in data],
                     x=[each['month'] for each in data],
                     low=[each['entry'] for each in data],
                   high=[each['exit'] for each in data])], 
        'layout': {'title': 'Overview of Monthly performance'}}


@app.callback(
        dash.dependencies.Output('table', 'data'),
       (dash.dependencies.Input('exchange-select', 'value'),
        dash.dependencies.Input('leverage-select', 'value'),
        dash.dependencies.Input('date-range', 'start_date'),
        dash.dependencies.Input('date-range', 'end_date'),))

def update_table(exchange, leverage, start_date, end_date):
    dff = filter_df(df, exchange, leverage, start_date, end_date)
    return dff.to_dict('records')


@app.callback(
    [
        dash.dependencies.Output('market-returns', 'children'),
        dash.dependencies.Output('strat-returns', 'children'),
        dash.dependencies.Output('strat-vs-market', 'children'),
    ],
    (
        dash.dependencies.Input('exchange-select', 'value'),
        dash.dependencies.Input('leverage-select', 'value'),
        dash.dependencies.Input('date-range', 'start_date'),
        dash.dependencies.Input('date-range', 'end_date'),

    )
)
def update_indicators(exchange, leverage, start_date, end_date):
    dff = filter_df(df, exchange, leverage, start_date, end_date)
    data = calc_returns_over_month(dff)
    btc_returns = calc_btc_returns(dff)
    strat_returns = calc_strat_returns(dff)
    strat_vs_market = strat_returns - btc_returns

    return f'{btc_returns:0.2f}%', f'{strat_returns:0.2f}%', f'{strat_vs_market:0.2f}%'


@app.callback(
        dash.dependencies.Output('pnl-types', 'figure'),
       (dash.dependencies.Input('exchange-select', 'value'),
        dash.dependencies.Input('leverage-select', 'value'),
        dash.dependencies.Input('date-range', 'start_date'),
        dash.dependencies.Input('date-range', 'end_date'),))
def update_bar_chart(exchange, leverage, start_date, end_date):
    dff = filter_df(df, exchange, leverage, start_date, end_date)
    chart=pnl_types(dff)   
    return{'data':chart,'layout': {'title': 'Pnl vs Trade Type','height':500}}


@app.callback(
        dash.dependencies.Output('daily-btc', 'figure'),
       (dash.dependencies.Input('exchange-select', 'value'),
        dash.dependencies.Input('leverage-select', 'value'),
        dash.dependencies.Input('date-range', 'start_date'),
        dash.dependencies.Input('date-range', 'end_date'),))

def update_line_chart(exchange, leverage, start_date, end_date):
    dff = filter_df(df, exchange, leverage, start_date, end_date)
    chart= go.Scatter(x=dff['Entry time'], y=dff['BTC Price'], mode='lines')
    return {'data':[chart],'layout': {'title': 'Daily  BTC Price','height':500}}


@app.callback(
        dash.dependencies.Output('balance', 'figure'),
       (dash.dependencies.Input('exchange-select', 'value'),
        dash.dependencies.Input('leverage-select', 'value'),
        dash.dependencies.Input('date-range', 'start_date'),
        dash.dependencies.Input('date-range', 'end_date'),))

def update_balance_chart(exchange, leverage, start_date, end_date):
    dff = filter_df(df, exchange, leverage, start_date, end_date)
    chart= go.Line(x=dff['Entry time'], y=dff['Exit balance'])
    return {'data':[chart],'layout': {'title': 'Balance Overtime','height':500}}




if __name__ == '__main__':app.run_server(debug=True,host= '0.0.0.0')
