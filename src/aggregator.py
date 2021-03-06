import argparse
from typing import Dict, List

import config_file
import parser_engine
import os
from glob import glob
from operator import itemgetter

class Aggregator:
    def __init__(self, recategorize = True, logger = None):
        if logger is None:
            logfile = os.getcwd() + "/aggregator.logs"
            self.logger = open(logfile, 'w')
        else:
            self.logger = logger
        self.pdf_parser = parser_engine.Parser(recategorize, self.logger)

    def load_transactions_from_datafile(self, datafile):
        account_transactions: List[Dict[str, str]] = []
        if not os.path.exists(datafile):
            return account_transactions
        if not os.path.getsize(datafile) > 0:
            return account_transactions
        dfile = open(datafile, 'r')
        for line in dfile.readlines():
            tokens = line.strip('\n').split(';')
            transaction_block = dict(zip(config_file.transaction_template, tokens))
            account_transactions.append(transaction_block)
        return account_transactions

    def move_to_archive(self, pdf_stmt, account_archive_dir):
        pdf_basename = pdf_stmt.split('/')[-1]
        new_pdfstmt_loc = account_archive_dir + "/" + pdf_basename
        os.rename(pdf_stmt, new_pdfstmt_loc)
        self.logger.write("[Aggregator] Moved %s to %s \n" % (pdf_stmt, new_pdfstmt_loc))

    def write_transactions(self, all_transactions, account_datafile):
        sorted_transactions = sorted(all_transactions, key=itemgetter('date'))
        twriter = open(account_datafile, 'w')
        for block in sorted_transactions:
            #twriter.write(config_file.writer_format.format(block['date'], block['desc'], block['tval'], block['origin'], block['category'], block['balance'], block['hashid']))
            block_str = ';'.join(block.values())
            twriter.write(block_str + '\n')


    def parse_account_dir(self, account_dir):
        tokens = account_dir.split('/')
        account_name = tokens[2] if tokens[-1] is '' else tokens[-1]
        account_type = (account_name.split('.'))[1]
        account_archive_dir = account_dir + config_file.archive_subdir
        account_datafile = account_dir + "/" + account_name + ".datafile.csv"
        all_transactions = self.load_transactions_from_datafile(account_datafile)
        hashid_list = []
        for ldict in all_transactions:
            hashid_list.append(ldict['hashid'])

        if not os.path.exists(account_archive_dir):
            os.makedirs(account_archive_dir)
        for pdf_stmt in glob(os.path.join(account_dir,"*.{}".format("pdf"))):
            stmt_transactions = self.pdf_parser.parse_statement(pdf_stmt, account_type)
            for stmt_transaction_block in stmt_transactions:
                if stmt_transaction_block['hashid'] not in hashid_list:
                    all_transactions.append(stmt_transaction_block)
                    hashid_list.append(stmt_transaction_block['hashid'])
                else:
                    self.logger.write('[Aggregator] PdfFile: %s | Transaction: %s already found in DB\n' % (pdf_stmt, stmt_transaction_block))
            self.move_to_archive(pdf_stmt, account_archive_dir)

        self.write_transactions(all_transactions, account_datafile)

    def parse_super_dir(self, super_dir):
        subdir_list = next(os.walk(super_dir))[1]
        for account_dir_basename in subdir_list:
            account_dir = super_dir + "/" + account_dir_basename
            self.parse_account_dir(account_dir)

arg_parser = argparse.ArgumentParser()
arg_parser.add_argument('--parse_all_statements', default=False, type=bool, help='Parse all statements in Accounts subdirs')
arg_parser.add_argument('--parse_account_statements', help='Parse only the given account')
arg_parser.add_argument('--super_dir', default=config_file.default_accounts_dir, help='Budgetified parsing_dir')
arg_parser.add_argument('--recategorize', default=True, help='Only use to say not to recategorize')

args = arg_parser.parse_args()
aggregator = Aggregator(args.recategorize)

if args.parse_all_statements:
    aggregator.parse_super_dir(args.super_dir)
elif args.parse_account_statements is not None:
    aggregator.parse_account_dir(args.parse_account_statements)
