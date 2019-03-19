#!/usr/bin/env python
from sys import argv
from decimal import *
from collections import deque
import os
import datetime
import re
import ledger
import getrates

'''Queries a journal for lots, reduces them, & returns ledger-format lot reductions to sdout.

$ python TaxingLots.py 'filename' 'query'

    filename  -- a ledger file, entries sorted by date
    query     -- a ledger query for commodities to augment / reduce
[NOT IMPLEMENTED YET:
    method    -- FIFO [LIFO] (defaults to FIFO) ]

Globably, this program:

 1. Reads a ledger journal 'filename' and a ledger 'query' (what
    commodity or commodities are you interested in?) as arguments,
    and returns matching posts using the python ledger bridge, which
    must be compiled with your version of ledger. Its output defaults
    to sdout, so it never modifies its imput files. Your ledger journal
    must be sorted by date.

 2. Creates a list "stack" of commodity lots with dates and cost basis.
    Currently it handles bitcoin (BTC), litecoin (LTC), and ether (ETH),
    reducing from the oldest lot of each commodity first (First In, First
    Out, FIFO).

 3. Reads the ledger line by line, outputing to stout.
    A. If a line has commodity reductions matching the query,
       the lot sales are reduced agains holdings in the "stack" of lots
       for that particular commodity.
    B. The resulting ledger notation is inserted in the line (or lines
       when multiple lots are booked against) and printed to stdout.
    C. Output currently assumes USD as reference currency for all lot cost
       basis calculations, to keep the IRS happy.
        
Notes:

Ledger is a powerful, double-entry accounting system that is accessed from the
UNIX command-line. Ledger is written by John Wiegley, released under the BSD
license, and is available at http://ledger-cli.org.

TaxingLots.py returns lot reductions using Ledger's syntax, assuming USD as the
reference currency for taxation purposes. It does not check that the
transactions are balanced, since Ledger already does that. It simply manages
booking and reducing commodity/cryptocurrency lots, but leaves the user in
control of the overall transaction structure.

The program requires a CSV file with exchange rates for all commodities. Modify
the getrates() function according to your needs and your rates file.

The program also inserts Income:CapitalGains legs where necessary when reducing
lots. This gives Ledger the CapitalGains explicitly, so when you run TaxingLot's
output back through Ledger, you may have to manually adjust some transactions due
to currency exchange rate losses and/or gains.

I keep my ledger file in the actual currencies or cryptocurrencies that I
transact in. With this program, I can convert to USD to calculate and report
capital gains/losses with a USD basis for each transaction. The program adds
exchange rate price declarations to the output. The original currencies or
commodities are reported in comments on the same line as the converted USD rate.

This is my first attempt at Python. Pull requests are welcome. However, I may
be slow to respond as I'm learning python and busy with my family and my
non-programming work.

Writen by Joel Swanson. Version 0.03. Copyright 2017-2018. Licensed under
the GNU General Public License (GPL) Version 3. Absolutely no warranty,
this program provided 'as is'. See https://www.gnu.org/licenses/gpl.html.'''

script, filename, query = argv

def convert_to_USD(foreign):
    """Converts lot pricing to USD. Takes string "{[amount] [commodity symbol], returns list of amount and rate in USD"""
    foreign = foreign.split(' ')
    rates = getrates.getrates(date)
    USDEUR, USDBTC, USDGBP, USDLTC, UAHUSD, JPYUSD, CHFUSD, XAUUSD, XAGUSD = float(rates[2]), float(rates[3]), float(rates[4]), float(rates[5]), float(rates[6]), float(rates[7]), float(rates[8]), float(rates[9]), float(rates[10])
    if foreign[1] == 'EUR':
        priceUSD = float(foreign[0]) * USDEUR
    elif foreign[1] == 'BTC':
        priceUSD = float(foreign[0]) * USDBTC
    elif foreign[1] == 'GBP':
        priceUSD = float(foreign[0]) * USDGBP
    elif foreign[1] == 'LTC':
        priceUSD = float(foreign[0]) * USDLTC
    elif foreign[1] == 'UAH':
        priceUSD = float(foreign[0]) * 1/UAHUSD
    elif foreign[1] == 'JPY':
        priceUSD = float(foreign[0]) * JPYUSD
    elif foreign[1] == 'CHF':
        priceUSD = float(foreign[0]) * CHFUSD
    elif foreign[1] == 'XAU':
        priceUSD = float(foreign[0]) * XAUUSD
    elif foreign[1] == 'XAG':
        priceUSD = float(foreign[0]) * XAGUSD
    elif foreign[1] == 'USD':
        priceUSD = float(foreign[0])
    else:
        priceUSD = "Add currency or commodity %s to function 'convert_to_USD()'" % foreign[1]
    return priceUSD

def strip_AZ(cstring):
    """Given a string, removes initial & final ('A' & 'Z') character from a string, returns string."""
    cstring = cstring[1:]
    cstring = cstring[:(len(cstring)-1)]
    return cstring

def reduce_lot(stack, reduce_stack):
    """Given lists of holdings & reductions, reduces oldest lot & returns list of lot info with updated lot size.

    This function implements lot reductions following the priciple of First In, First Out (FIFO).

    In the returned 'lot_info' list, the updated_lot variable gives the new balance of the lot after
    reduction. If its negative, that indicates the lot was fully reduced. The absolute value of the
    negative 'updated_lot' needs to be reduce from the next lot holding in the stack for reduction.

    Lot and reduction pricing is converted to USD, so ledger can use the cost basis to calculate any
    capital gains or capital losses."""
    
    lot_date, lot, lot_unit, lot_price = stack[0][0], float(stack[0][1]), stack[0][2], float(convert_to_USD(strip_AZ(stack[0][3])))

    reduction_date, reduction, reduction_unit = reduce_stack[0][0], abs(float(reduce_stack[0][1])), reduce_stack[0][2] 
    original_reduction_price = strip_AZ(reduce_stack[0][3])
    original_reduction_unit = original_reduction_price.split(' ')
    original_reduction_unit = original_reduction_unit[1]

    reduction_price, reduction_account = convert_to_USD(strip_AZ(reduce_stack[0][3])), reduce_stack[0][4]
            
    updated_lot = lot - reduction

    lot_info = [lot_date, lot, lot_unit, lot_price, reduction_date, reduction, reduction_unit, original_reduction_price, reduction_price, reduction_account, updated_lot, original_reduction_unit]

    return lot_info

def duration_held(purchase_date, sale_date):
    """Takes purchase and sale dates, returns number of days commodity held. Depend on datetime module."""
    buydate = datetime.datetime.strptime(purchase_date, "%Y-%m-%d")
    selldate = datetime.datetime.strptime(sale_date, "%Y-%m-%d")
    duration = (selldate - buydate).days
    return duration

def capital_gains(amt, bought_at, sold_at):
    """Given three numbers (an amount, a buy price, and a sell price), returns gains as income.

    In the standard account equation, income is negative, and that convention is followed. """
    amt, bought_at, sold_at = float(amt), float(bought_at), float(sold_at)
    gains = (bought_at * amt) - (sold_at * amt)
    return gains

def gains_info(amt, bought_at, sold_at, duration):
    if duration < 0:
        info = "    ; You can't reduce from a future lot."
    elif duration > 365:
        long_term_gains = capital_gains(amt, bought_at, sold_at)
        gains.append(long_term_gains)
        info = "    Income:CapitalGainsLT       %.2f USD    ; Held for %.0f days: long-term gains/losses apply." % (long_term_gains, duration)
    else:
        short_term_gains = capital_gains(amt, bought_at, sold_at)
        gains.append(short_term_gains)
        info = "    Income:CapitalGains          %.2f USD" % short_term_gains
    return info

def is_empty(any_structure):
    if any_structure:
        return False
    else:
        return True

print("comment")
print("\nQuerying %r via the ledger bridge.\n") % filename

# Use's the ledger python bridge to read from a ledger journal file.
# NOTE: ledger file must be sorted by date, via "ledger print --sort date"
#
# Each posting is broken into a list of strings, s.
# s[0] is date, s[1] is amount, s[2] unit, s[3] price, s[4] account
# "lots" is a list of s strings.
#

lots = []

for post in ledger.read_journal(filename).query(query):
    s = "%s %s %s" % (post.date, post.amount, post.account)
#    print s
    
    s = s.split(' ')
    if len(s) == 9:
        s[3] = "%s %s" % (s[3], s[4])
        del s[4:8]
    if len(s) == 7:
        s[3] = "%s %s" % (s[3], s[4])
        del s[4]
        del s[4]
    elif len(s) == 4:
        s.insert(3, "{1.00000000 BTC}")
    lots.append(s)

# Creates lists for cryptocurrency holdings, a list "stack" to hold
# whichever cryptocurrency is actively being reduced, and a "reduce_stack"
# list of the reductions to be applied.

BTC_holdings = []
ETH_holdings = []
LTC_holdings = []
stack = []
reduce_stack = []

gains = []   # to accumulate capital gains from gains_info()

for i in range (len(lots)):
    amt = float(lots[i][1])      # changing string to float
    if amt > 0:                  # Adding positive lots to "stack".
        if lots[i][2] == 'BTC':
            BTC_holdings.append(lots[i])
        elif lots[i][2] == 'ETH':
            ETH_holdings.append(lots[i])
        elif lots[i][2] == 'LTC':
            LTC_holdings.append(lots[i])
    elif amt < 0:
        if lots[i][2] == 'BTC,':
            lots[i][2] = 'BTC'
        elif lots[i][2] == 'LTC,':
            lots[i][2] = 'LTC'
        reduce_stack.append(lots[i])
        
print "\nBitcoin (BTC) lots:"

for i in range(len(BTC_holdings)):
    amt = float(BTC_holdings[i][1])
    BTC_holdings[i][1] = amt
    print "BTC_holdings[%s] %s %s %s %s" % (i, BTC_holdings[i][0], BTC_holdings[i][1], BTC_holdings[i][2], BTC_holdings[i][3])

if BTC_holdings == stack:
    print "No lots to be reduced."
    
print "\nEther (ETH) lots:"

for i in range(len(ETH_holdings)):
    amt = float(ETH_holdings[i][1])
    ETH_holdings[i][1] = amt
    print "ETH_holdings[%s] %s %s %s %s" % (i, ETH_holdings[i][0], ETH_holdings[i][1], ETH_holdings[i][2], ETH_holdings[i][3])

if ETH_holdings == stack:
    print "No lots to be reduced."

print "\nLitecoin (LTC) lots"

for i in range(len(LTC_holdings)):
    amt = float(LTC_holdings[i][1])
    LTC_holdings[i][1] = amt
    print "LTC_holdings[%s] %s %s %s %s" % (i, LTC_holdings[i][0], LTC_holdings[i][1], LTC_holdings[i][2], LTC_holdings[i][3])

if LTC_holdings == stack:
    print "No lots to be reduced."
    
print "\nReductions to be applied:"

for i in range(len(reduce_stack)):
    date_r = reduce_stack[i][0]
    reduction = float(reduce_stack[i][1])
    unit_r = reduce_stack[i][2]
    price_r = reduce_stack[i][3]
    price_r = price_r[1:]
    price_r = price_r[:(len(price_r)-1)]
    print "reduce_stack[%s] %s %s %s %s" % (i, date_r, reduction, unit_r, price_r)

print "end comment"
print

# Read 'filename' line by line, replacing lines with commodity reductions
# with modified line(s) inserting cost basis & date info showing which
# lot is reduced.

f = open(filename)
lines = []
lines = f.readlines()
tx_num = 0
date = '2009-01-03'    # sample date to turn 'date'into a global variable; also the date of the Bitcoin genesis block.
USDEUR = USDBTC = USDGBP = USDLTC = UAHUSD = JPYUSD = CHFUSD = XAUUSD = XAGUSD = 0.0


for i in range(len(lines)):
    # For each date in ledger file, assigns conversion rate variables relative to USD
    m = re.search(r'(^(\d{4}-\d{2}-\d{2}))', lines[i])
    if m:
        date = m.group(1)
        rates = getrates.getrates(date)       # USD/EUR = rates[2], USD/BTC = rates[3], USD/GBP = rates[4], USD/LTC = rates[5], UAH/USD = rates[6], JPY/USD = rates[7], CHF/USD = rates[8], XAU/USD = rates[9], XAG/USD = rates[10]
        time = getrates.gettime(rates[1])     # Specific time of rate conversion = time
        USDEUR, USDBTC, USDGBP, USDLTC, UAHUSD, JPYUSD, CHFUSD, XAUUSD, XAGUSD = float(rates[2]), float(rates[3]), float(rates[4]), float(rates[5]), float(rates[6]), float(rates[7]), float(rates[8]), float(rates[9]), float(rates[10])

        print "P %s EUR %.4f USD" % (date, USDEUR)
        print "P %s GBP %.4f USD" % (date, USDGBP)
        print "P %s BTC %.4f USD" % (date, USDBTC)
        print "P %s LCT %.4f USD\n" % (date, USDLTC)
#        print "P %s USD %.4f UAH" % (date, UAHUSD)
#        print "P %s USD %.4f JPY" % (date, JPYUSD)
#        print "P %s USD %.4f CHF" % (date, CHFUSD)
#        print "P %s XAU %.4f USD" % (date, 1/XAUUSD)
#        print "P %s XAG %.4f USD\n" % (date, 1/XAGUSD)
                
        tx_num = tx_num + 1

    m = re.search(r'Assets:Crypto.*\s{1,}(-\d+(\.\d+)?)\s(BTC|ETH|LTC)', lines[i])
    if m:
        stack = []
        if m.group(3) == 'BTC':                                   # Matches commodity lot to commodity found in journal file.
            stack = BTC_holdings                                  # Assigns current commodity holdings to the "stack" variable.
        elif m.group(3) == 'ETH':
            stack = ETH_holdings
        elif m.group(3) == 'LTC':
            stack = LTC_holdings

        if m.group(3) == stack[0][2]:                             # Check that commodity symbols match, because one can't subtract APPL from ORANGE.

            if float(m.group(1)) == float(reduce_stack[0][1]):    # Check that reduction from ledger python bridge matches what the regex read from the journal file.

                linfo = reduce_lot(stack, reduce_stack)           # Reduces lot and provides list of lot info 'linfo' variables to print results.
                lot_date, lot, lot_unit, lot_price, reduction_date, reduction, reduction_unit, original_reduction_price, reduction_price, reduction_account, updated_lot, original_reduction_unit  = linfo[0], linfo[1], linfo[2], linfo[3], linfo[4], linfo[5], linfo[6], linfo[7], linfo[8], linfo[9], linfo[10], linfo[11]

                while updated_lot <= 0:                           # Does reduction exceed size of lot? If so, clear lot & remove cleared lot from stack,
                      
                    print "    %s    -%s %s {%.2f USD} [%s] (lot cleared) @ %.2f USD" % (reduction_account, lot, reduction_unit, lot_price, lot_date, reduction_price)
                    if original_reduction_unit != 'USD':
                        print "    ; Reduction price converted from @ %s" % (original_reduction_price)
                    print "    ; Lot size remaining: %s %s - %s %s (reduction) = %s %s" % (lot, lot_unit, reduction, reduction_unit, updated_lot, lot_unit)

                    duration = duration_held(lot_date, reduction_date)

                    print "%s" % gains_info(lot, lot_price, reduction_price, duration)
                    
                    if is_empty(stack):
                        print "No more %s lots to reduce, 'stack' is empty." % lot_unit
                        break

                    stack = stack[1:]                   # Remove cleared lot from stack. This sets stack[0] to next oldest lot.

                    reduce_stack[0][1] = updated_lot    # Sets remainder of lot reduction as amount to be reduced next.
                    
                    linfo = reduce_lot(stack, reduce_stack)
                    lot_date, lot, lot_unit, lot_price, reduction_date, reduction, reduction_unit, original_reduction_price, reduction_price, reduction_account, updated_lot, original_reduction_unit = linfo[0], linfo[1], linfo[2], linfo[3], linfo[4], linfo[5], linfo[6], linfo[7], linfo[8], linfo[9], linfo[10], linfo[11]

            print "    %s    -%s %s {%.2f USD} [%s] @ %.2f USD" % (reduction_account, reduction, reduction_unit, lot_price, lot_date, reduction_price)
            if original_reduction_unit != 'USD':
                print "    ; Reduction price converted from @ %s" % (original_reduction_price)
            print "    ; Lot size remaining: %s %s - %s %s (reduction) = %s %s" % (lot, lot_unit, reduction, reduction_unit, updated_lot, lot_unit)

            duration = duration_held(lot_date, reduction_date)

            print "%s" % gains_info(reduction, lot_price, reduction_price, duration)

            stack[0][1] = updated_lot               # Sets remainder of lot reduction as amount in next held lot.

            reduce_stack = reduce_stack[1:]         # Removes reduced commodity sale from list of reductions to be booked.   
            
            if m.group(3) == 'BTC':                               # Update commodities holdings with reductions
                BTC_holdings = stack
            elif m.group(3) == 'ETH':
                ETH_holdings = stack
            elif m.group(3) == 'LTC':
                LTC_holdings = stack
        else:
            print "    ; UH OH: Symbols %s and %s don't match. See line %s in journal file." % (m.group(3), stack[0][2], i)
    else:                                                         # Switching cost basis prices to USD.
        m = re.search(r'(^(\d{4}-\d{2}-\d{2}).*)\n', lines[i])
        m1a = re.search(r'(Assets:Crypto:Ether\s{1,}(\d+(\.\d+)?)\sETH\s@\s)((\d+(\.\d+)?)\sBTC)', lines[i])
        m1b = re.search(r'(Assets:Crypto:Litecoin\s{1,}(\d+(\.\d+)?)\sLTC\s@\s)((\d+(\.\d+)?)\sBTC)', lines[i])
#        m2 = re.search(r'(Assets:Crypto:Bitcoin\s{1,}(\d+(\.\d+)?)\sBTC)\n', lines[i])
        m3 = re.search(r'((Assets|Expenses|Liabilities).*\s{1,})((-?\d+(\.\d+)?)\s(EUR|GBP))', lines[i])
        m4 = re.search(r'(Income:CapitalGains)', lines[i])
        if m:
            print "%s           ; Transaction No. %s" % (m.group(1), tx_num)
        elif m1a:
            USDETH = convert_to_USD(m1a.group(4))                  # Converts ETH price in BTC to price in USD
            print "    %s%.2f USD     ; Originally @ %s BTC" % (m1a.group(1), USDETH, m1a.group(5)) 
        elif m1b:
            USDLTC = convert_to_USD(m1b.group(4))                  # Converts LTC price in BTC to price in USD
            print "    %s%.f2 USD     ; Originally @ %s BTC" % (m1b.group(1), USDLTC, m1b.group(5)) 
#        elif m2:
#            print "    %s @ %.2f USD\n" % (m2.group(1), 1/USDBTC),
        elif m3:
            if m3.group(6) == 'EUR':
                EUR_ref = convert_to_USD(m3.group(3))
                print "    %s%.2f USD     ; Originally @ %s EUR" % (m3.group(1), EUR_ref, m3.group(4))
            elif m3.group(6) == 'GBP':
                GBP_ref = convert_to_USD(m3.group(3))
                print "    %s%.2f USD     ; @ %s GBP" % (m3.group(1), GBP_ref, m3.group(4))
        elif m4:
            pass
        else:
            print "%s" % lines[i],
            
print "\ncomment"

sumBTC = sumETH = sumLTC = 0

print "\nBitcoin (BTC) lots:"

for i in range(len(BTC_holdings)):
    BTC_holdings[i][1] = float(BTC_holdings[i][1])
    sumBTC = sumBTC + BTC_holdings[i][1]
    print "    %s %s %s %s" % (BTC_holdings[i][0], BTC_holdings[i][1], BTC_holdings[i][2], BTC_holdings[i][3])

print "Total holdings: %s BTC" % sumBTC
    
print "\nEther (ETH) lots:"

for i in range(len(ETH_holdings)):
    ETH_holdings[i][1] = float(ETH_holdings[i][1])
    sumETH = sumETH + ETH_holdings[i][1]
    print "    %s %s %s %s" % (ETH_holdings[i][0], ETH_holdings[i][1], ETH_holdings[i][2], ETH_holdings[i][3])

print "Total holdings: %s ETH" % sumETH
    
print "\nLitecoin (LTC) lots"

for i in range(len(LTC_holdings)):
    LTC_holdings[i][1] = float(LTC_holdings[i][1])
    sumLTC = sumLTC + LTC_holdings[i][1]
    print "    %s %s %s %s" % (LTC_holdings[i][0], LTC_holdings[i][1], LTC_holdings[i][2], LTC_holdings[i][3])

print "Total holdings: %s LTC" % sumLTC
    
print "\nReductions to be applied:"

for i in range(len(reduce_stack)):
    date_r = reduce_stack[i][0]
    reduction = float(reduce_stack[i][1])
    unit_r = reduce_stack[i][2]
    price_r = reduce_stack[i][3]
    price_r = price_r[1:]
    price_r = price_r[:(len(price_r)-1)]
    print "reduce_stack[%s] %s %s %s %s" % (i, date_r, reduction, unit_r, price_r)

if is_empty(reduce_stack):
    print "    All lots have been reduced.\n"

capitalgains = 0
for i in range(len(gains)):
    capitalgains = capitalgains + gains[i]

print "Capital gains: %.2f USD." % capitalgains

print "end comment\n"
