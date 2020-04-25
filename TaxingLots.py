#!/usr/bin/env python
from sys import argv
from decimal import *
from collections import deque
import os
import datetime
import re
import ledger
import getrates

'''Queries journal for lots, reduces them, & returns lot reductions to sdout.

$ python TaxingLots.py 'filename' Assets:Crypto [-d]

    filename  -- a ledger file, entries sorted by date

    [-d]      -- turn on debuging / verbose output

[NOT IMPLEMENTED YET:
    query     -- generic ledger query to augment or reduce commodities
    method    -- FIFO [LIFO] (defaults to FIFO) ]

Globably, this program:

 0. Reads a ledger journal 'filename', queries for reductions of any
    assets under Assets:Crypto, and returns matching posts using the
    python ledger bridge, which must be compiled with your version of
    ledger. Its output defaults to sdout, so it never modifies its imput
    files. Your ledger journal must be sorted by date.

 1. Creates a list "stack" of commodity lots with dates and cost basis.
    Currently it handles bitcoin (BTC), litecoin (LTC), and ether (ETH),
    reducing from the oldest lot of each commodity first (First In, First
    Out, FIFO).

 2. Reads the ledger line by line, outputing to stout.
    A. If a line has commodity reductions matching the query,
       the lot sales are reduced agains holdings in the "stack" of lots
       for that particular commodity.
    B. The resulting ledger notation is inserted in the line (or lines
       when multiple lots are booked against) and printed to stdout.
    C. Print lines not reducing a commodity directly to stdout, making the
       following slight modifications:
        1) For each transaction's date, print historic exchange rates
           above the transaction, and add a commented transaction number
        2) Convert non-USD postings to USD, and insert comment with
           original posting amount and currency or commodity. I have to
           use USD as my reference currency for my US taxes.

 3. Prefaces output with ledger comments listing the crypto lots to be
    reduced. Follows output with ledger comments listing remaining lots
    held and cumulative capital gains in USD (recall in the standard
    accounting equation, income is negative, thus capital gains are negative
    and capital losses are positive.

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
lots. This gives Ledger the CapitalGains explicitly, so when you run
TaxingLot's output back through Ledger, you may have to manually adjust some
transactions due to currency exchange rate losses and/or gains.

I keep my ledger file in the actual currencies or cryptocurrencies that I
transact in. With this program, I can convert to USD to calculate and report
capital gains/losses with a USD basis for each transaction. The program adds
exchange rate price declarations to the output. The original currencies or
 commodities are reported in comments on the same line as the converted USD rate.

This is my first attempt at Python. Pull requests are welcome. However, I may
be slow to respond as I'm learning python and busy with my family and my
non-programming work.

Writen by Joel Swanson. Version 0.03. Copyright 2017-2019. Licensed under
the GNU General Public License (GPL) Version 3. Absolutely no warranty,
this program provided 'as is'. See https://www.gnu.org/licenses/gpl.html.'''

script, filename, query, opt = argv

def convert_to_USD(foreign):
    """Converts lot pricing to USD. Takes string "[amount] [commodity symbol]", returns list of amount and rate in USD"""
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
    """Given a string, removes initial & final ('A' & 'Z') character from a
    string, returns string.

    This little function removes the curly braces from Ledger's price info.
    E.g., "{417.50 EUR}" would become "417.50 EUR"."""
    
    cstring = cstring[1:]
    cstring = cstring[:(len(cstring)-1)]
    return cstring

def reduce_lot(stack, reductions):
    """Given lists of holdings & reductions, reduces oldest lot & returns list
    of lot info with updated lot size.

    This function implements lot reductions following the priciple of First In,
    First Out (FIFO).

    In the returned 'lot_info' list, the updated_lot variable gives the new
    balance of the lot after reduction. If its negative, that indicates the lot
    was fully reduced. The absolute value of the negative 'updated_lot' needs
    to be reduce from the next lot holding in the stack for reduction.

    Lot and reduction pricing is converted to USD, so ledger can use the cost
    basis to calculate any capital gains or capital losses."""
    
    lot_date, lot, lot_unit, lot_price = stack[0][0], float(stack[0][1]), stack[0][2], float(convert_to_USD(strip_AZ(stack[0][3])))

    reduction_date, reduction, reduction_unit = reductions[0][0], abs(float(reductions[0][1])), reductions[0][2] 
    original_reduction_price = strip_AZ(reductions[0][3])   
    original_reduction_unit = original_reduction_price.split(' ')
    original_reduction_unit = original_reduction_unit[1]

    reduction_price, reduction_account = convert_to_USD(strip_AZ(reductions[0][3])), reductions[0][4]
            
    updated_lot = lot - reduction

    duration = duration_held(lot_date, reduction_date)

    lot_info = [lot_date, lot, lot_unit, lot_price, reduction_date, reduction, reduction_unit, original_reduction_price, reduction_price, reduction_account, updated_lot, original_reduction_unit, duration]

    return lot_info

def display_commodity(commodity):
    """Given a commodity symbol, determines decimal precision """
    # TODO learn better way to do this (2019-10-15)
    is_fiat = {'EUR','GBP','UAH','CHF','JPY','USD'}
    is_crypto = {'BTC','LTC','ETH'}
    is_commodity ={'XAU','XAG'}
    if commodity in is_fiat or is_commodity:
        display_decimals = 2
    if commodity in is_crypto:
        display_decimals = 8
    return display_decimals

def reductions_remaining(reductions, i):
    """Prints lot sales to be reduced. Takes 'reductions' list as input. """
    date_r = reductions[i][0]
    reduction = float(reductions[i][1])
    unit_r = reductions[i][2]
    price_r = reductions[i][3]
    price_r = price_r[1:]
    price_r = price_r[:(len(price_r)-1)]
    reductions_info = "reductions[%s] %s %.8f %s %s" % (i, date_r, reduction, unit_r, price_r)
    return reductions_info

def duration_held(purchase_date, sale_date):
    """Takes purchase and sale dates, returns number of days commodity held. Depend on datetime module."""
    buydate = datetime.datetime.strptime(purchase_date, "%Y-%m-%d")
    selldate = datetime.datetime.strptime(sale_date, "%Y-%m-%d")
    duration = (selldate - buydate).days
    return duration

def cap_gains(amt, bought_at, sold_at):
    """Given three numbers (an amount, a buy price, and a sell price), returns gains as income.

    In the standard accounting equation, income is negative, and that convention is followed. """
    amt, bought_at, sold_at = float(amt), float(bought_at), float(sold_at)
    gains = (bought_at * amt) - (sold_at * amt)
    return gains

def lprint_gains(amt, bought_at, sold_at, duration):
    """Determines whether gains are long or short-term. Returns gains info in ledger format. """
    # TODO (2020-04-23): Fix/Clean up this function
    # accumulating gains inside this function isn't a pure function.
    
    if duration < 0:
        info = "    ; You can't reduce from a future lot."
    elif duration > 365:
        long_term_gains = cap_gains(amt, bought_at, sold_at)
        gains.append(long_term_gains)
        info = "    Income:CapitalGainsLT       %.2f USD    ; Held for %.0f days: long-term gains/losses apply." % (long_term_gains, duration)
    else:
        short_term_gains = cap_gains(amt, bought_at, sold_at)
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
# "holdings" is a dictionary with commodity symbols for keys, and each
# value is a list of s strings from the postings.
#
# For altcoins, your ledger journal file must present them relative to
# bitcoin. For example,
#
#    2016-11-10 * ether sale                                                         
#        Assets:Crypto:Ether                 -40.0 ETH
#        Assets:Crypto:Bitcoin               1.000 BTC
#
# shows that the ether in terms of bitcoin, which will result in a reduction
# lot of "2016-11-10 -40.00000000 ETH {0.025 BTC}". This is due to a lack of
# reliable altcoin to USD exchange data, so we use bitcoin as the reference
# currency.

print('%s' % (query))

holdings = {}    # keys: commodity symbols; values: commodity postings
reductions = []  # commodity postings to be reduced from holdings
stack = []       # hold whichever cryptocurrency is actively being reduced
gains = []       # accumulate capital gains from lprint_gains()

for post in ledger.read_journal(filename).query(query):
    s = "%s %s %s" % (post.date, post.amount, post.account)
    posts = s.split()
    date = '%s' % (post.date)
    rates = getrates.getrates(date)
    commodity = '%s' % (post.amount.commodity)
    amount = '%s' % (post.amount)
    if len(posts) == 4:     # TODO Convert getrates to dict
        if commodity == 'BTC':
            annotation = '{%.2f USD} [%s]' % (float(rates[3]), date)
        elif commodity == 'LTC':
            annotation = '{%.2f USD} [%s]' % (float(rates[5]), date)
        amount = '%s %s' % (amount, annotation)
        s = '%s %s %s' % (date, amount, post.account)
    print(s)

    s = list(s.split(' '))
    if len(s) == 7:
        s[3] = "%s %s" % (s[3], s[4])  # Combine amount and unit in {}
        del s[4:6]                     # Remove redundant unit and date
    
    if commodity in holdings:          # Fill holdings with positive commodity
        if commodity == s[2]:          # postings. Reductions sorted out. 
            amt = float(s[1])
            if amt > 0:
                holdings[commodity].append(s)
            elif amt < 0:
                reductions.append(s)
    else:
        holdings[commodity] = [s]

for commodity in holdings:     # Print lists of commodity holdings
    print('\n%s lots:' % (commodity))
    for i in range(len(holdings[commodity])):
        amt = float(holdings[commodity][i][1])
        print("holdings[%s][%s] %s %.8f %s %s" % (commodity, i, holdings[commodity][i][0], amt, commodity, holdings[commodity][i][3]))

print("\nReductions to be applied:")
for i in range(len(reductions)):
    redux_info = reductions_remaining(reductions, i)
    print('%s' % redux_info)
    
print("end comment")
print

# Read 'filename' line by line, replacing lines with commodity reductions
# with modified line(s) inserting cost basis & date info showing which
# lot is reduced.

f = open(filename)
lines = []
lines = f.readlines()

tx_num = 0
date = '2009-01-03'    # sample date to turn 'date'into a global variable; also the date of the Bitcoin genesis block.
USDEUR = USDBTC = USDGBP = USDLTC = UAHUSD = JPYUSD = CHFUSD = XAUUSD = XAGUSD = CNYBTC= 0.0   # initialize all rates.

for i in range(len(lines)):
    # For each date in ledger file, assigns conversion rate variables relative to USD
    m = re.search(r'(^(\d{4}-\d{2}-\d{2}).*)\n', lines[i])
    # re.search(r'(^(\d{4}-\d{2}-\d{2}))', lines[i])
    if m:
        date = m.group(2)
        # USD/EUR = rates[2], USD/BTC = rates[3], USD/GBP = rates[4],
        # USD/LTC = rates[5], UAH/USD = rates[6], JPY/USD = rates[7],
        # CHF/USD = rates[8], XAU/USD = rates[9], XAG/USD = rates[10],
        # CNY/BTC = rates[11]
        rates = getrates.getrates(date)
        # Specific time of rate conversion = time
        time = getrates.gettime(rates[1])
        try:
            # As of 2019-04-06, don't have a historical Litecoin price
            # history data before 2013-04-28.
            if date < 2013-4-28:             
                USDEUR, USDBTC, USDGBP, UAHUSD, JPYUSD, CHFUSD, XAUUSD, XAGUSD = float(rates[2]), float(rates[3]), float(rates[4]), float(rates[6]), float(rates[7]), float(rates[8]), float(rates[9]), float(rates[10])
                print("P %s EUR %.2f USD" % (date, USDEUR))
                print("P %s GBP %.2f USD" % (date, USDGBP))
                print("P %s BTC %.2f USD            ; %.8f BTC/XAU" % (date, USDBTC, 1/(USDBTC/XAUUSD)))
                print("P %s XAU %.2f USD\n" % (date, XAUUSD))
            else:
                USDEUR, USDBTC, USDGBP, USDLTC, UAHUSD, JPYUSD, CHFUSD, XAUUSD, XAGUSD = float(rates[2]), float(rates[3]), float(rates[4]), float(rates[5]), float(rates[6]), float(rates[7]), float(rates[8]), float(rates[9]), float(rates[10])
                print("P %s EUR %.2f USD" % (date, USDEUR))
                print("P %s GBP %.2f USD" % (date, USDGBP))
                print("P %s BTC %.2f USD             ; %.8f BTC/XAU" % (date, USDBTC, 1/(USDBTC/XAUUSD)))
                print("P %s LTC %.2f USD" % (date, USDLTC))
                print("P %s XAU %.2f USD\n" % (date, XAUUSD))
        except ValueError:
            print("comment\n    ; Error on line %s \nend comment" % (i))

        tx_num = tx_num + 1
        print("%s           ; Transaction No. %s" % (m.group(1), tx_num))
        
    # Find postings which reduce crypto assets (i.e., where Assets:Crypto has a negative value)
    # TODO replace 'Assets:Crypto' with query to generalize this commodity reduction script
    m = re.search(r'Assets:Crypto.*\s{1,}(-\d+(\.\d+)?)\s(BTC|ETH|LTC)', lines[i])
    if m:
        stack = []
        commodity = m.group(3)         # Matches commodity lot to commodity found in journal file.
        stack = holdings[commodity]    # Assigns current commodity holdings to the "stack" variable.
        
        # Check that commodity symbols match, because one can't subtract APPL from ORANGE.
        if m.group(3) == stack[0][2]:
            if '-d' == opt:
                print('          ; DEBUG \'show reductions\'')
                for i in range(len(stack)):
                    for j in range(len(stack[i])):
                        print('          ;   stack[%s][%s]: %s' % (i, j, stack[i][j]))
                print('          ; END DEBUG\n')

            # Check that reduction from ledger python bridge matches what the regex read from the journal file.
            if float(reductions[0][1]) == float(m.group(1)):    

                # Reduces lot and provides list of lot info 'linfo' variables to print results.
                linfo = reduce_lot(stack, reductions)
                lot_date, lot, lot_unit, lot_price, reduction_date, reduction, reduction_unit, original_reduction_price, reduction_price, reduction_account, updated_lot, original_reduction_unit, duration = linfo[0], linfo[1], linfo[2], linfo[3], linfo[4], linfo[5], linfo[6], linfo[7], linfo[8], linfo[9], linfo[10], linfo[11], linfo[12]

                # Does reduction exceed size of lot? If so, clear lot & remove cleared lot from stack,
                while updated_lot <= 0:
                      
                    print("    %s    -%.8f %s {%.2f USD} [%s] (lot cleared) @ %.2f USD" % (reduction_account, lot, reduction_unit, lot_price, lot_date, reduction_price))
                    if '-d' == opt:
                        if original_reduction_unit != 'USD':
                            print("    ; Reduction price converted from @ %s" % (original_reduction_price))
                        print("    ; Lot size remaining: %.8f %s - %.8f %s (reduction) = %s %s" % (lot, lot_unit, reduction, reduction_unit, updated_lot, lot_unit))

                    print("%s" % lprint_gains(lot, lot_price, reduction_price, duration))
                    
                    if is_empty(stack):
                        print("    ; No more %s lots to reduce, 'stack' is empty." % lot_unit)
                        break

                    # Remove cleared lot from stack. This sets stack[0] to next oldest lot.
                    stack = stack[1:]

                    # Sets remainder of lot reduction as amount to be reduced next.
                    reductions[0][1] = updated_lot
                    
                    linfo = reduce_lot(stack, reductions)
                    lot_date, lot, lot_unit, lot_price, reduction_date, reduction, reduction_unit, original_reduction_price, reduction_price, reduction_account, updated_lot, original_reduction_unit, duration = linfo[0], linfo[1], linfo[2], linfo[3], linfo[4], linfo[5], linfo[6], linfo[7], linfo[8], linfo[9], linfo[10], linfo[11], linfo[12]

            print("    %s    -%.8f %s {%.2f USD} [%s] @ %.2f USD" % (reduction_account, reduction, reduction_unit, lot_price, lot_date, reduction_price))
            if '-d' == opt:
                if original_reduction_unit != 'USD':
                    print("    ; Reduction price converted from @ %s" % (original_reduction_price))
                print("    ; Lot size remaining: %.8f %s - %.8f %s (reduction) = %s %s" % (lot, lot_unit, reduction, reduction_unit, updated_lot, lot_unit))

            print("%s" % lprint_gains(reduction, lot_price, reduction_price, duration))

            # Sets remainder of lot reduction as amount in next held lot.
            stack[0][1] = updated_lot

            # Removes reduced commodity sale from list of reductions to be booked.   
            reductions = reductions[1:]

            # Update commodities holdings with reductions
            holdings[commodity] = stack

        else:
            print("    ; UH OH: Symbols %s and %s don't match. See line %s in journal file." % (m.group(3), stack[0][2], i))
    else:                   # Switching cost basis prices to USD.
        m = re.search(r'(^(\d{4}-\d{2}-\d{2}).*)\n', lines[i])
        m1a = re.search(r'(Assets:Crypto:Ether\s{1,}(\d+(\.\d+)?)\sETH\s@\s)((\d+(\.\d+)?)\sBTC)', lines[i])
        m1b = re.search(r'(Assets:Crypto:LTC\s{1,}(\d+(\.\d+)?)\sLTC\s@\s)((\d+(\.\d+)?)\sBTC)', lines[i])
        m3 = re.search(r'((Assets|Expenses|Liabilities).*\s{1,})((-?\d+(\.\d+)?)\s(EUR|GBP))', lines[i])
        m3a = re.search(r'(Expenses:Fees.*\s{1,})((\d+(\.\d+)?)\s(BTC|LTC))', lines[i])
        m3b = re.search(r'(Assets:Crypto:LTC\s{1,}((\d+(\.\d+)?)\sLTC))', lines[i])
        m4 = re.search(r'(Income:CapitalGains)', lines[i])
        if m:
            pass   #            print('%s           ; Transaction No. %s' % (m.group(1), tx_num))
        elif m1a:
            USDETH = convert_to_USD(m1a.group(4))                  # Converts ETH price in BTC to price in USD
            print("    %s%.2f USD     ; Originally @ %s BTC" % (m1a.group(1), USDETH, m1a.group(5)))
        elif m1b:
            USDLTC = convert_to_USD(m1b.group(4))                  # Converts LTC price in BTC to price in USD
            print("    %s%.f2 USD     ; Originally @ %s BTC" % (m1b.group(1), USDLTC, m1b.group(5)))
        elif m3:
            if m3.group(6) == 'EUR':
                EUR_ref = convert_to_USD(m3.group(3))
                print("    %s%.2f USD     ; Originally @ %s EUR" % (m3.group(1), EUR_ref, m3.group(4)))
            elif m3.group(6) == 'GBP':
                GBP_ref = convert_to_USD(m3.group(3))
                print("    %s%.2f USD     ; @ %s GBP" % (m3.group(1), GBP_ref, m3.group(4)))
        elif m3a:
            if m3a.group(5) == 'BTC':
                print('%s @ %.2f USD' % (lines[i][:-1], USDBTC))
            elif m3a.group(5) == 'LTC':
                print('%s @ %.2f USD' % (lines[i][:-1], USDLTC))
        elif m3b:
            print('%s @ %s USD' % (lines[i][:-1], USDLTC))
        elif m4:
            pass
        else:
            lines[i] = lines[i].rstrip()  # remove '\n' from lines
            print(lines[i])
            
print("\ncomment")

for commodity in holdings:         # Print commodity lots and total holdings.
    total = 0
    print('Remaining %s lots:' % commodity)
    for i in range(len(holdings[commodity])):
        amt = float(holdings[commodity][i][1])
        total = float(total) + amt
        print("%s %f %s %s" % (holdings[commodity][i][0], amt, commodity, holdings[commodity][i][3]))
    print('Total holdings: %f %s.\n' % (float(total), commodity))

if is_empty(reductions):
    print("    All lots have been reduced.\n")
else:
    print("Reductions to be applied:")
    for i in range(len(reductions)):
        redux_info = reductions_remaining(reductions, i)
        print('%s' % redux_info)

capitalgains = 0
for i in range(len(gains)):
    capitalgains = capitalgains + gains[i]

print("Capital gains: %.2f USD." % capitalgains)

print("end comment\n")
