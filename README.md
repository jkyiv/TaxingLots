2020-02-07 WIP - I'm updating to Python 3.7, and currently (i.e., if this note
is still here) my Python 3.7 script isn't fully working. Sorry. I hope to fix it soon.

* Overview

Querys a journal for lots, reduces them, & returns ledger-format lot reductions to sdout.

$ python TaxingLots.py 'filename' 'query' 'option'

    filename  -- a ledger file, entries sorted by date
    query     -- a ledger query for commodities to augment / reduce.
                 (Only works with 'Assets:Crypto' at the moment.)
    option    -- currently, '-d' turns on debug options. Any other
                 option will be ignored.

Sample usage:

$ python TaxingLots.py sample.journal Assets:Crypto

should give you the same output as the "sample-output" file in this repository.

* Globably, this program:

 1. Reads a ledger journal 'filename' and a ledger 'query' (what
    commodity or commodities are you interested in?) as arguments,
    and returns matching posts using the python ledger bridge, which
    must be compiled with your version of ledger. Its output defaults
    to sdout, so it never modifies its imput files.

 2. Creates a list or stack of commodity lots with dates and cost basis.
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
        
* Notes

Ledger is a powerful, double-entry accounting system that is accessed from the
UNIX command-line. Ledger is written by John Wiegley, released under the BSD
license, and is available at http://ledger-cli.org. Ledger has inspired a number of other plain-text accounting programs, as well as a community of active users and contributers. To learn more, see https://plaintextaccounting.org/.

On Debian (and I assume derivative distributions like Ubuntu or Linux Mint), in
addition to the "ledger" package, the "python-ledger" package provides you with
the necessary Python bindings so that TaxingLots.py can read ledger data files.

TaxingLots.py returns lot reductions using Ledger's syntax, assuming USD as the
reference currency for taxation purposes. It does not check that the
transactions are balanced, since Ledger already does that. It simply manages
booking and reducing commodity/cryptocurrency lots, but leaves the user in
control of the overall transaction structure.

The program requires a CSV file with exchange rates for all commodities. Modify
the getrates() function according to your needs and your rates file.

The program also inserts Income:CapitalGains legs where necessary when reducing
lots. This gives Ledger the CapitalGains explicitly, so when you run TaxingLot's output back through Ledger, you may have to manually adjust some transactions due to currency exchange rate losses and/or gains.

I keep my ledger file in the actual currencies or cryptocurrencies that I
transact in. With this program, I can convert to USD to calculate and report
capital gains/losses with a USD basis for each transaction. The program adds
exchange rate price declarations to the output. The original currencies or
commodities are reported in comments on the same line as the converted USD rate.

This is my first attempt at Python. Pull requests are welcome. However, I may
be slow to respond as I'm learning python and busy with my family and my
non-programming work.

Writen by Joel Swanson. Version 0.03. Copyright 2017-2020. Licensed under
the GNU General Public License (GPL) Version 3. Absolutely no warranty,
this program provided 'as is'. See https://www.gnu.org/licenses/gpl.html.


* Roadmap *

**  gains/losses report

    I plan to write a function to generate gains/losses output report,
    Until this is done, for a quick and dirty look at all lot reductions,
    use grep on the output as follows:

    $ python TaxingLots.py [input.dat] Assets:Crypto d | grep -A 1 'lot reduced'

**  Update to Python 3

**  Detect & exclude internal transfers

    2020-06-24 Add ability to track user's internal wallet to wallet
    transfers, without double-counting assets, and yet calculating
    gains/losses on network fees paid.

**  Add testing
