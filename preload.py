import argparse


def preload(parser: argparse.ArgumentParser):
    parser.add_argument(
        "--remotemoe",
        action="store_true",
        help="ремоте_мое",
    )
    parser.add_argument(
        "--lhr_life",
        action="store_true",
        help="лхр_лайф",
    )
    parser.add_argument(
        "--serveo",
        action="store_true",
        help="сервео",
    )
    parser.add_argument(
        "--flara",
        action="store_true",
        help="клаудфлара",
    )
    parser.add_argument(
        "--all_links",
        action="store_true",
        help="все ссылки",
    )
