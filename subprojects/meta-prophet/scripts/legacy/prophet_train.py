import pandas as pd
from prophet import Prophet

df = pd.read_csv("NQ_4h_2025.csv")
print(df.columns)

ready_df = df[["datetime", "close"]].copy()
ready_df.rename(columns={"datetime": "ds", "close": "y"}, inplace=True)
print(ready_df.head())

model = Prophet()
model.fit(ready_df)
future = model.make_future_dataframe(periods=100, freq="4h")
future.tail()
forecast = model.predict(future)
print(forecast[["ds", "yhat", "yhat_lower", "yhat_upper"]].tail())

figure = model.plot(forecast)
figure.show()

figure2 = model.plot_components(forecast)
figure2.show()

from prophet.plot import plot_plotly, plot_components_plotly
plot_plotly(model, forecast).show()
plot_components_plotly(model, forecast).show()  


forecast[["ds", "yhat", "yhat_lower", "yhat_upper"]].to_csv("forecast.csv", index=False)
forecasted_results = pd.read_csv("forecast.csv")
print(forecasted_results.head())




