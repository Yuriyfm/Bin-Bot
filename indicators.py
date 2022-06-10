import math

import numpy as np
import statsmodels.api as sm
import pandas as pd


def get_rsi(df):
    delta = df['close'].diff()
    up = delta.clip(lower=0)
    down = -1 * delta.clip(upper=0)
    ema_up = up.ewm(com=14, adjust=False).mean()
    ema_down = down.ewm(com=14, adjust=False).mean()
    rs = ema_up / ema_down
    df['RSI'] = 100 - (100 / (1 + rs))
    return df


def get_ema(df):
    df['EMA_3'] = df['close'].ewm(span=3).mean()
    df['EMA_7'] = df['close'].ewm(span=7).mean()
    return df


def get_sma(df):
    df['SMA_2'] = df['close'].rolling(window=2).mean()
    df['SMA_5'] = df['close'].rolling(window=5).mean()
    return df


def get_atr(source_DF, n):
    df = source_DF.copy()
    df['H-L'] = abs(df['high'] - df['low'])
    df['H-PC'] = abs(df['high'] - df['close'].shift(1))
    df['L-PC'] = abs(df['low'] - df['close'].shift(1))
    df['TR'] = df[['H-L', 'H-PC', 'L-PC']].max(axis=1, skipna=False)
    df['ATR'] = df['TR'].rolling(n).mean()
    df_temp = df.drop(['H-L', 'H-PC', 'L-PC'], axis=1)
    return df_temp


def deal(deals):
    deals.append(1)


def get_slope(series, n):
    array_sl = [j * 0 for j in range(n - 1)]
    for j in range(n, len(series) + 1):
        y = series[j - n:j]  # итоговые значения первых n свечей
        x = np.array(range(n))  # массив [1, 2, 3, ... n-1]
        x_sc = (x - x.min()) / (x.max() - x.min())
        y_sc = (y - y.min()) / (y.max() - y.min())
        x_sc = sm.add_constant(x_sc)
        model = sm.OLS(y_sc, x_sc)
        results = model.fit()
        array_sl.append(results.params[-1])
    slope_angle = (np.rad2deg(np.arctan(np.array(array_sl))))
    return np.array(slope_angle)


def getMaxMinChannel(DF, n):
    maxx = 0
    minn = DF['low'].max()
    for i in range(1, n):
        if maxx < DF['high'][len(DF) - i]:
            maxx = DF['high'][len(DF) - i]
        if minn > DF['low'][len(DF) - i]:
            minn = DF['low'][len(DF) - i]
    return maxx, minn


def get_bollinger_bands(df):
    df['SMA_20'] = df['close'].rolling(window=20).mean()
    rstd = df['close'].rolling(window=20).std()
    df['upper_band'] = df['SMA_20'] + 2 * rstd
    df['lower_band'] = df['SMA_20'] - 2 * rstd
    return df


def sma(price, period):
    sma = price.rolling(period).mean()
    return sma


def ao(price, period1, period2):
    median = price.rolling(2).median()
    short = sma(median, period1)
    long = sma(median, period2)
    ao = short - long
    ao_df = pd.DataFrame(ao).rename(columns={'close': 'ao'})
    return ao_df


def get_sma_slope(sma, n):
    slope = np.arctan((sma - sma.shift(n)) / n) * 180 / np.pi
    return slope
