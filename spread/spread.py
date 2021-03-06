#!/usr/bin/env python3
import json
import time
import ccxt


def beep():
    print("\a\a\a\a\a")


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


config = json.load(open('config.json'))
Base = config["Base"]
Quote = config["Quote"]
Contract = config["Contract"]
Spread_threshold = config["Spread_threshold"]
Close_threshold = config["Close_threshold"]
Min_MarginRatio = config["Min_MarginRatio"]
Min_trade_amount = config["Min_trade_amount"]
Max_trade_amount = config["Max_trade_amount"]
Limit_close_trade_amount = config["Limit_close_trade_amount"]
close_trade_amount = 0
Trade_mode = config["trade_mode"]
side = 0
init_balance = 0
miss_balance_btc = 0
total_fund = 0
profit = 0
need_check_balance = True

long_amount_A = 0
short_amount_A = 0

open_long = 1
open_short = 2
close_long = 3
close_short = 4
spread_hit = 0
close_hit = 0
trade_hit = 0

A = ccxt.binance(config["binance"])
B = ccxt.okex(config["okex"])
A.load_markets()
B.load_markets()

A_pair = ""
B_pair = Base + '-' + Quote

lock = 0
lock_price_B = 0
lock_amount_B = 0
lock_side = ""


for symbol in A.markets:
    if Base in symbol:
        A_pair = symbol
        break

for symbol in B.markets:
    if B_pair in symbol:
        market = B.markets[symbol]
        if market['info']['alias'] == Contract:
            B_pair = market['symbol']
            break

count = 0

while True:
    try:
        print("=" * 80)
        print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
              "count:", count,
              "trade_hit:", trade_hit,
              "spread_hit:", spread_hit, "close_hit:", close_hit,
              "trade_mode:", Trade_mode,
              "max_trade_amount:", Max_trade_amount,
              "limit_close_trade_amount:", "%.3f" %Limit_close_trade_amount,
              "balance_usd:", "%.1f" %total_fund,
              "profit:", "%.1f" %profit)
        time.sleep(2)
        if count % 5 == 0 or need_check_balance:
            # time.sleep(5)
            # marginRatio A
            balance_A = A.fetchBalance()
            marginRatio_A = float(balance_A["info"]["totalMarginBalance"]) / \
                            (10 * float(balance_A["info"]["totalInitialMargin"])) if \
                            float(balance_A["info"]["totalInitialMargin"]) != 0 else 1

            # marginRatio B
            balance_B = B.fetchBalance()
            marginRatio_B = float(balance_B["info"]["info"]['btc']['margin_ratio'])

            # trade avaliable Amount BTC
            order_book_A = A.fetch_order_book(A_pair)
            bid0_price_A = order_book_A['bids'][0][0]
            trade_availableAmount_A = (float(balance_A["info"]["totalMarginBalance"]) / 10 \
                                      / Min_MarginRatio - \
                                      float(balance_A["info"]["totalInitialMargin"])) / \
                                      bid0_price_A
            # TODO position need binance api to update
            positionRisk = A.fapiPrivateGetPositionRisk()
            markPrice_A = float(positionRisk[0]["markPrice"])
            entryPrice_A = float(positionRisk[0]["entryPrice"])
            unRealizedProfit_A = float(positionRisk[0]["unRealizedProfit"])
            if (markPrice_A > entryPrice_A and unRealizedProfit_A > 0) or \
               (markPrice_A < entryPrice_A and unRealizedProfit_A < 0):
                long_amount_A = float(positionRisk[0]["positionAmt"])
                short_amount_A = 0.0
            else:
                short_amount_A = -float(positionRisk[0]["positionAmt"])
                long_amount_A = 0.0

            # trade available Amount BTC
            trade_availableAmount_B = (float(balance_B["info"]["info"]['btc']['equity']) / \
                                       Min_MarginRatio / 10 \
                                       - float(balance_B["info"]["info"]['btc']['margin_frozen']))
            position_B = B.futures_get_instrument_id_position({"instrument_id": B_pair})
            hold_long_avail_qty_B = float(position_B["holding"][0]["long_avail_qty"])
            hold_short_avail_qty_B = float(position_B["holding"][0]["short_avail_qty"])
            hold_long_qty_B = float(position_B["holding"][0]["long_qty"])
            hold_short_qty_B = float(position_B["holding"][0]["short_qty"])
            order_book_B = B.fetch_order_book(B_pair)
            bid0_price_B = order_book_B['bids'][0][0]

            sell_availAmount_A = trade_availableAmount_A * 10 + 2 * long_amount_A
            buy_availAmount_A = trade_availableAmount_A * 10 + 2 * short_amount_A

            sell_availAmount_B = trade_availableAmount_B * 10 + \
                                 2 * hold_long_avail_qty_B * 100 / bid0_price_B
            buy_availAmount_B = trade_availableAmount_B * 10 + \
                                2 * hold_short_avail_qty_B * 100 / bid0_price_B
            total_fund = float(balance_B["info"]["info"]['btc']['equity']) * bid0_price_A + \
                         float(balance_A["info"]["totalMarginBalance"]) + \
                         miss_balance_btc * bid0_price_A
            if count == 0:
                init_balance = total_fund
            profit = total_fund - init_balance
            print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                  "Total USDT:", "%.1f" %total_fund,
                  "Profit:", "%.2f" %profit)
            need_check_balance = False

        count += 1
        print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
              A.id.ljust(7), "marginRatio(big safe):", "%3.4f" %marginRatio_A)
        print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
              B.id.ljust(7), "marginRatio(big safe):", "%3.4f" %marginRatio_B)
        print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
              A.id.ljust(7),
              "sell available BTC amount:", "%3.4f" %sell_availAmount_A,
              "buy available BTC amount:", "%3.4f" %buy_availAmount_A)
        print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
              B.id.ljust(7),
              "sell available BTC amount:", "%3.4f" %sell_availAmount_B,
              "buy available BTC amount:", "%3.4f" %buy_availAmount_B)
        print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()), A.id.ljust(7),
              "position long:", "%.3f" %long_amount_A,
              "position short:", "%.3f" %short_amount_A)

        print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
              B.id.ljust(7),
              "position long:", "%.3f" %(hold_long_qty_B * 100 / bid0_price_B),
              "position short:", "%.3f" %(hold_short_qty_B * 100 / bid0_price_B))
        print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
              "Total BTC:", "%.3f" %((total_fund - float(balance_A["info"]["totalMarginBalance"])) / \
                                     bid0_price_A),
              "Total Position:", "%.3f" %((hold_long_qty_B - hold_short_qty_B) * 100 / \
                                          bid0_price_B + long_amount_A - short_amount_A))

        AopenOrders = A.fetchOpenOrders(symbol=A_pair)
        print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
              A.id.ljust(7), "order:", AopenOrders)
        BopenOrders = B.fetchOpenOrders(symbol=B_pair)
        print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
              B.id.ljust(7), "order:", BopenOrders)

        order_book_A = A.fetch_order_book(A_pair)
        bid0_price_A = order_book_A['bids'][0][0]
        bid0_amount_A = order_book_A['bids'][0][1]
        ask0_price_A = order_book_A['asks'][0][0]
        ask0_amount_A = order_book_A['asks'][0][1]
        bidask_spread_A = ask0_price_A - bid0_price_A
        timestamp_A = time.time()
        print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()), A.id.ljust(7),
                "bids:",
                "%5.2f" %bid0_price_A, "%5.2f" %bid0_amount_A,
                "asks:",
                "%5.2f" %ask0_price_A, "%5.2f" %ask0_amount_A,
                "bss:",
                "%5.2f" %bidask_spread_A)

        order_book_B = B.fetch_order_book(B_pair)
        bid0_price_B = order_book_B['bids'][0][0]
        bid0_amount_B = order_book_B['bids'][0][1] * 100 / bid0_price_B
        ask0_price_B = order_book_B['asks'][0][0]
        ask0_amount_B = order_book_B['asks'][0][1] * 100 / ask0_price_B
        bidask_spread_B = ask0_price_B - bid0_price_B
        timestamp_B = time.time()
        print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()), B.id.ljust(7),
                "bids:",
                "%5.2f" %bid0_price_B, "%5.2f" %bid0_amount_B,
                "asks:",
                "%5.2f" %ask0_price_B, "%5.2f" %ask0_amount_B,
                "bss:",
                "%5.2f" %bidask_spread_B)
        AaskBbid_spread = (ask0_price_A - bid0_price_B)/bid0_price_B
        BaskAbid_spread = (ask0_price_B - bid0_price_A)/bid0_price_A
        print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
              B.id.ljust(7), "->", A.id.ljust(7),
              "profit:",
              bcolors.FAIL,
              "%+.4f" %AaskBbid_spread,
              bcolors.ENDC)
        print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
              A.id.ljust(7), "->", B.id.ljust(7),
              "profit:",
              bcolors.FAIL,
              "%+.4f" %BaskAbid_spread,
              bcolors.ENDC)

        if timestamp_B - timestamp_A > 0.7:
            print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                  "time delay:", "%.6f" %(timestamp_B - timestamp_A), "too big!")
            continue
        else:
            print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                  "time dalay:", "%.6f" %(timestamp_B - timestamp_A))

        if len(AopenOrders) > 0 or len(BopenOrders) > 0 or lock == 1:
            print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                  "Some orders is not close or order locking!",
                  "price:", lock_price_B, "amount:", lock_amount_B, "side:", lock_side)
            continue

        if BaskAbid_spread < Close_threshold:
            close_hit += 1
            if Trade_mode is not True or \
               close_trade_amount > Limit_close_trade_amount:
                continue
            AaskBbid_amount = min(bid0_amount_A, ask0_amount_B, Max_trade_amount,
                                  sell_availAmount_A, buy_availAmount_B)
            B_amount = int(AaskBbid_amount * bid0_price_B / 100)
            AaskBbid_amount = float("%.3f" %(B_amount * 100 / bid0_price_B))
            if AaskBbid_amount < Min_trade_amount:
                print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                      "Too small trade amount", AaskBbid_amount)
                continue

            need_check_balance = True
            print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                  A.id.ljust(7), "sell", AaskBbid_amount, "(BTC)", bid0_price_A,
                  B.id.ljust(7), "buy", B_amount, "(100USD)", ask0_price_B)

            Aask = A.createLimitSellOrder(A_pair, AaskBbid_amount, bid0_price_A)
            print(Aask)
            lock = 1
            lock_price_B = ask0_price_B
            lock_amount_B = B_amount
            lock_side = "buy"
            close_trade_amount += AaskBbid_amount
            print("." * 10)

            position_B = B.futures_get_instrument_id_position({"instrument_id": B_pair})
            hold_short_avail_qty_B = int(position_B["holding"][0]["short_avail_qty"])
            if hold_short_avail_qty_B > B_amount:
                Bbid = B.create_order(B_pair, close_short, "buy",
                                      B_amount,
                                      ask0_price_B)
                print(Bbid)
            else:
                if hold_short_avail_qty_B != 0:
                    Bbid = B.create_order(B_pair, close_short, "buy",
                                          hold_short_avail_qty_B,
                                          ask0_price_B)
                    print(Bbid)
                Bbid = B.create_order(B_pair, open_long, "buy",
                                      B_amount - hold_short_avail_qty_B,
                                      ask0_price_B)
                print(Bbid)
            lock = 0
            beep()
            trade_hit += 1
            os.system("say Transaction order has been placed")

        if BaskAbid_spread > Spread_threshold:
            spread_hit += 1

            if Trade_mode != True:
                continue
            BaskAbid_amount = min(ask0_amount_A, bid0_amount_B, Max_trade_amount,
                                  sell_availAmount_B, buy_availAmount_A)
            B_amount = int(BaskAbid_amount * ask0_price_B / 100)
            BaskAbid_amount = float("%.3f" %(B_amount * 100 / ask0_price_B))
            if BaskAbid_amount < Min_trade_amount:
                print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                      "Too small trade amount", BaskAbid_amount)
                continue

            need_check_balance = True
            print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                  A.id.ljust(7), "buy", BaskAbid_amount, "(BTC)", ask0_price_A,
                  B.id.ljust(7), "sell", B_amount, "(100USD)", bid0_price_B)
            Abid = A.createLimitBuyOrder(A_pair, BaskAbid_amount, ask0_price_A)
            print(Abid)
            lock = 1
            lock_price_B = bid0_price_B
            lock_amount_B = B_amount
            lock_side = "sell"
            print("." * 10)
            close_trade_amount -= BaskAbid_amount

            position_B = B.futures_get_instrument_id_position({"instrument_id": B_pair})
            hold_long_avail_qty_B = int(position_B["holding"][0]["long_avail_qty"])
            if hold_long_avail_qty_B > B_amount:
                Bask = B.create_order(B_pair, close_long, "sell",
                                      B_amount,
                                      bid0_price_B)
                print(Bask)
            else:
                if hold_long_avail_qty_B != 0:
                    Bask = B.create_order(B_pair, close_long, "sell",
                                          hold_long_avail_qty_B,
                                          bid0_price_B)
                    print(Bask)
                Bask = B.create_order(B_pair, open_short, "sell",
                                      B_amount - hold_long_avail_qty_B,
                                      bid0_price_B)
                print(Bask)
            lock = 0
            beep()
            trade_hit += 1
            os.system("say Transaction order has been placed")

    except Exception as err:
        print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()), err)
        time.sleep(10)
        continue
