#!/Usr/bin/env python
from sys import argv
from decimal import *
from collections import deque
import os
import datetime
import re

def getrates(date):
    """Takes date (YYYY-mm-dd), returns a list with: comma separated date, timestamp, and conversion rates.

    Its up to you to provide exchange rates. Example format for a .csv exchange rates file:

date,timestamp,USDEUR,USDBTC,USDGBP,USDLTC,UAHUSD,JPYUSD,CHFUSD,XAUUSD,XAGUSD,EURBTC,BTCBTC,GBPBTC,UAHBTC,JPYBTC,CHFBTC,XAUBTC,XAGBTC, from currencylayer.com
2018-05-16,1526515199,1.18189579888666,8343.9275,1.35470190187481,139.65,26.2099989999913,110.367995999965,1.00057007122845,0.000774452318767,0.061387354216585,7059.782688,1,6159.235097,218694.331431,920902.556944,8348.684133,6.461974,512.211633,
2018-05-17,1526601599,1.17952191819878,8069.6688,1.351204773399,139.56,26.155001000041,110.833028726036,1.00166016974575,0.000775341114371,0.060862420524619,6841.474224,1,5972.202703,211062.195534,894385.83392,8083.06582,6.256746,491.139576,
2018-05-18,1526653808,1.17688435714284,8069.7475,1.34707407147203,132.70,26.1100010000313,110.869003000032,0.998329815276128,0.000775193771552,0.0609570252353,6856.873788,1,5990.574439,210701.115295,894684.859787,8056.269531,6.255618,491.907802,

    For this example:   list[0] is date
                        list[1] is timestamp
                        list[2] is USD/EUR
                        list[3] is USD/BTC
                        list[4] is USD/GBP
                        list[5] is USD/LTC
                        list[6] is UAH/USD
                        list[7] is JPY/USD
                        list[8] is CHF/USD
                        list[9] is XAU/USD
                        list[10] is XAG/USD
                        list[11] is CNY/BTC    (I added CNY for November 2013 only)

    TODO: add graceful error handling if function is given a date that's not in rates file.
    Currently this will generate a NoneType object error when the program is run, so verify
    that all dates have conversion history in your rates file."""

    f = open("rates.csv")

    lines = []

    lines = f.readlines()

    for i in range(len(lines)):
        if date in lines[i]:
            line = lines[i].rstrip()
            line = lines[i].split()
            rates = list(line)
            rates = rates[0].split(',')
            if rates is not None:
                return rates

def gettime(timestamp):
    """Takes a UNIX timestame, returns UTC time in %Y-%m-%d %H:%M:% format."""
    timeUTC = datetime.datetime.utcfromtimestamp(int(timestamp)).strftime('%Y-%m-%d %H:%M:%S')
    return timeUTC

