# Orange Search
A Scrapy spider with purpose to scrape document from https://cr.ocgov.com/recorderworks/ in search by date of record.

The input would be start_date and end_date. Spider would scan for all document within that date of recorded.

# How to run:
From root terminal of project, run following command.
Please replace start_date and end_date with your desired date.
Date format shoudl be: mm\dd\yyyy

```
scrapy crawl orange_county -a start_date=12/1/2018 -a end_date=12/5/2018
```
