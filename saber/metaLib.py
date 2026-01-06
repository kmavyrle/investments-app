import MetaTrader5 as MT5

import datetime

import pandas as pd
import numpy as np



class meta5_wrapper:
    def __init__(self,mt5=MT5):
        login = 7347694
        pw = "1523@Rocket!!"
        server = "ICMarketsSC-MT5-2"
        self.mt5 = mt5
        self.mt5.initialize()
        self.mt5.login(login, password=pw, server=server),
        self.magic = 123456

        self.timeframe_dict = {'1m': self.mt5.TIMEFRAME_M1,
                        '5m': self.mt5.TIMEFRAME_M5,
                        '15m': self.mt5.TIMEFRAME_M15,
                        '30m': self.mt5.TIMEFRAME_M30,
                        '1h': self.mt5.TIMEFRAME_H1,
                        '4h': self.mt5.TIMEFRAME_H4,
                        '1d': self.mt5.TIMEFRAME_D1,
                        '1w': self.mt5.TIMEFRAME_W1,
                        '1mn': self.mt5.TIMEFRAME_MN1}
    
        self.asset_contract_size_map = {'US500': 1.0,
                                'CHINA50': 1.0,
                                'XBRUSD': 100.0,
                                'XAUUSD': 100.0,
                                'EURUSD': 100000.0,
                                'USDMXN': 100000.0,
                                'ETHUSD': 1.0}
    
        self.asset_min_lots_map = {'US500': 1.0,
                            'CHINA50': 1.0,
                            'XBRUSD': 0.5,
                            'XAUUSD': 0.01,
                            'EURUSD': 0.01,
                            'USDMXN': 0.01,
                            'ETHUSD': 1.0}
    
    def get_tick_data(self,asset,periodicity = '1d',timeframe = 250,end_dt = datetime.datetime.now()):
        '''
        Function gets the historical data for a specified asset

        Inputs:
        1. periodicity: indicates periodicity - 1m,5m, etc
        2. asset: What is the asset name
        3. timeframe: How many rows of data
        '''
        tf = self.timeframe_dict[periodicity]

        df = pd.DataFrame(self.mt5.copy_rates_from(asset,tf,end_dt,timeframe))
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df.set_index('time', inplace=True)
        df.index.name = 'Date'
        df['asset'] = [asset]*len(df)
        return df

    def _ensure_symbol(self,symbol):
        if not self.mt5.symbol_select(symbol, True):
            raise RuntimeError(f"Cannot select {symbol}")
        info = self.mt5.symbol_info(symbol)
        if info is None or not info.visible:
            raise RuntimeError(f"{symbol} not visible")
        return info

    def _pip_value(self, info):
        # 5/3 digits → pip = 10*point, else pip = point
        return (10 * info.point) if info.digits in (3, 5) else info.point
    

    def place_limit_order(self,symbol, side, volume_lots, price,
                        sl=None, tp=None, sl_pips=None, tp_pips=None,
                        deviation_points=20,
                        tif="GTC",            # "GTC" | "DAY" | "SPECIFIED" | "SPECIFIED_DAY"
                        expiry_minutes=60):   # used only for SPECIFIED / SPECIFIED_DAY
        side = side.upper()
        if side not in ("BUY_LIMIT", "SELL_LIMIT"):
            raise ValueError("side must be BUY_LIMIT or SELL_LIMIT")

        if not self.mt5.symbol_select(symbol, True):
            raise RuntimeError(f"Cannot select {symbol}")
        info = self.mt5.symbol_info(symbol); tick = self.mt5.symbol_info_tick(symbol)
        if not info or not tick: raise RuntimeError("No symbol info/tick")

        # sanity: limit prices must improve on market
        if side == "BUY_LIMIT" and not (price < tick.ask):
            raise ValueError(f"BUY_LIMIT price {price} must be < ask {tick.ask}")
        if side == "SELL_LIMIT" and not (price > tick.bid):
            raise ValueError(f"SELL_LIMIT price {price} must be > bid {tick.bid}")

        pip = (10*info.point) if info.digits in (3,5) else info.point
        if sl is None and sl_pips is not None:
            sl = price - sl_pips*pip if side=="BUY_LIMIT" else price + sl_pips*pip
        if tp is None and tp_pips is not None:
            tp = price + tp_pips*pip if side=="BUY_LIMIT" else price - tp_pips*pip

        # Time-in-force mapping (note: expiration ONLY for SPECIFIED / SPECIFIED_DAY)
        tif = tif.upper()
        if tif == "GTC":
            type_time = self.mt5.ORDER_TIME_GTC
            expiration = None
        elif tif == "DAY":
            type_time = self.mt5.ORDER_TIME_DAY
            expiration = None
        elif tif == "SPECIFIED":
            type_time = self.mt5.ORDER_TIME_SPECIFIED
            expiration = datetime.now(timezone.utc) + timedelta(minutes=expiry_minutes)
        elif tif == "SPECIFIED_DAY":
            type_time = self.mt5.ORDER_TIME_SPECIFIED_DAY
            expiration = datetime.now(timezone.utc) + timedelta(minutes=expiry_minutes)
        else:
            raise ValueError("tif must be GTC, DAY, SPECIFIED, or SPECIFIED_DAY")

        req = dict(
            action=self.mt5.TRADE_ACTION_PENDING,
            symbol=symbol,
            volume=volume_lots,
            type=getattr(self.mt5, f"ORDER_TYPE_{side}"),
            price=price,
            sl=0.0 if sl is None else sl,
            tp=0.0 if tp is None else tp,
            deviation=deviation_points,
            magic=self.magic,
            type_time=type_time,
            type_filling=self.mt5.ORDER_FILLING_RETURN,
        )
        if expiration is not None:
            req["expiration"] = expiration  # only for SPECIFIED / SPECIFIED_DAY

        r = self.mt5.order_send(req)
        if r is None:
            raise RuntimeError(f"order_send returned None: {self.mt5.last_error()}")
        if r.retcode != self.mt5.TRADE_RETCODE_DONE:
            raise RuntimeError(f"order_send failed: {r.retcode} {r.comment}")
        return r.order, r


    def place_market_order(
        self,
        symbol: str,
        side: str,                # "BUY" or "SELL"
        volume_lots: float,
        sl: float = None,         # absolute SL price (optional)
        tp: float = None,         # absolute TP price (optional)
        sl_pips: float = None,    # if sl not given
        tp_pips: float = None,    # if tp not given
        deviation_points: int = 20
    ):
        """
        Places a market order and returns (ticket, result).
        """

        # Validate side
        side = side.upper()
        if side not in ("BUY", "SELL"):
            raise ValueError("side must be 'BUY' or 'SELL'")

        # Select symbol
        if not self.mt5.symbol_select(symbol, True):
            raise RuntimeError(f"Cannot select {symbol}")
        info = self.mt5.symbol_info(symbol)
        tick = self.mt5.symbol_info_tick(symbol)
        if not info or not tick:
            raise RuntimeError("No symbol info/tick")

        # Get pip value (3/5 digit vs 2/4)
        pip = (10 * info.point) if info.digits in (3, 5) else info.point

        # Get current price depending on direction
        price = tick.ask if side == "BUY" else tick.bid

        # Calculate SL/TP if only pips provided
        if sl is None and sl_pips is not None:
            sl = price - sl_pips * pip if side == "BUY" else price + sl_pips * pip
        if tp is None and tp_pips is not None:
            tp = price + tp_pips * pip if side == "BUY" else price - tp_pips * pip

        # Build request
        req = dict(
            action=self.mt5.TRADE_ACTION_DEAL,
            symbol=symbol,
            volume=volume_lots,
            type=self.mt5.ORDER_TYPE_BUY if side == "BUY" else self.mt5.ORDER_TYPE_SELL,
            price=price,
            sl=0.0 if sl is None else float(sl),
            tp=0.0 if tp is None else float(tp),
            deviation=deviation_points,
            magic = self.magic,
            type_filling=self.mt5.ORDER_FILLING_IOC,  # safer default; can change to IOC/RETURN if needed
        )

        # Send order
        r = self.mt5.order_send(req)
        if r is None:
            raise RuntimeError(f"order_send returned None: {self.mt5.last_error()}")
        if r.retcode != self.mt5.TRADE_RETCODE_DONE:
            raise RuntimeError(f"order_send failed: {r.retcode} {r.comment}")

        return r.order, r

    def close_position_by_ticket(
        self,
        ticket: int,
        volume_lots: float | None = None,   # None = close full size
        deviation_points: int = 20
    ):
        """
        Market-closes an open position by ticket.
        - If volume_lots is None, closes the full remaining volume.
        - Handles partial closes (rounded to broker volume_step).
        - Uses opposite side at current bid/ask.
        Returns (deal_ticket, result).
        """
        # 1) Fetch the position
        pos_list = self.mt5.positions_get(ticket=ticket)
        if not pos_list:
            raise RuntimeError(f"No open position with ticket {ticket}")
        pos = pos_list[0]
        symbol = pos.symbol
        pos_side = pos.type  # 0=BUY, 1=SELL
        pos_volume = float(pos.volume)

        # 2) Ensure symbol and market data
        if not self.mt5.symbol_select(symbol, True):
            raise RuntimeError(f"Cannot select {symbol}")
        info = self.mt5.symbol_info(symbol)
        tick = self.mt5.symbol_info_tick(symbol)
        if not info or not tick:
            raise RuntimeError("No symbol info/tick")

        # 3) Determine close volume (partial/full) and round to step
        step = float(info.volume_step or 0.01)
        v = pos_volume if volume_lots is None else float(volume_lots)
        # cap to available volume
        v = min(v, pos_volume)
        # round to the nearest step
        v = round(v / step) * step
        # enforce broker min/max after rounding
        v = max(float(info.volume_min or step), min(v, float(info.volume_max or v)))
        if v <= 0:
            raise ValueError("Close volume rounds to 0; adjust volume_lots")

        # 4) Build opposite-side market order
        is_buy = (pos_side == self.mt5.POSITION_TYPE_BUY)
        order_type = self.mt5.ORDER_TYPE_SELL if is_buy else self.mt5.ORDER_TYPE_BUY
        price = tick.bid if is_buy else tick.ask

        req = dict(
            action=self.mt5.TRADE_ACTION_DEAL,
            symbol=symbol,
            volume=v,
            type=order_type,
            price=price,
            deviation=deviation_points,
            magic=self.magic,
            type_filling=self.mt5.ORDER_FILLING_IOC,
            position=ticket,  # required to close THIS position (hedging); harmless in netting
        )

        r = self.mt5.order_send(req)
        if r is None:
            raise RuntimeError(f"order_send returned None: {self.mt5.last_error()}")
        if r.retcode != self.mt5.TRADE_RETCODE_DONE:
            raise RuntimeError(f"close failed: {r.retcode} {r.comment}")
        return r.order, r


    def get_account_info(self):
        """
        Function gets account specific information
        """
        info = self.mt5.account_info()
        return info

    def get_symbol_info(self,symbol):
        info = self.mt5.symbol_info(symbol)
        return info 

    def get_trade_contract_size(self,symbol):
        info = self.get_symbol_info(symbol)
        return info.trade_contract_size   

    def get_positions(self):
        """
        Function returns existing positions of the account.
        """
        pos = self.mt5.positions_get()
        cols = ['ticket','time','time_msc','time_update','time_update_msc','type','magic','identifier','reason','volume','price_open','sl','tp','price_current','swap','profit','symbol','comment','external_id']
        df = pd.DataFrame(pos)
        df.columns = cols
        df['trade_contract_volume'] = [self.get_symbol_info(s).trade_contract_size for s in df['symbol']]
        df['trade_size'] = df['trade_contract_volume'] * df['volume']  
        df.set_index('symbol', inplace=True)
        df = (
            df.groupby(df.index)
            .apply(lambda x: x.to_dict(orient="list"))
            .to_dict()
        )

        #df = df.groupby(df.index).apply(lambda x: x.values.tolist()).to_dict()
        #df = df.to_dict(orient = 'index')
        return df

