from crawling_news_website import crawling_target_mediamap


if __name__ == "__main__":
    import pprint
    pprint.pp(crawling_target_mediamap(5, "mediamap.json"), indent=2)
