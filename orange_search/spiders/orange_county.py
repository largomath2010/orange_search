# -*- coding: utf-8 -*-
import scrapy,regex,logging
from datetime import datetime,timedelta
from urllib.parse import urlencode
from scrapy.selector import Selector
import uuid

class OrangeCountySpider(scrapy.Spider):
    name = 'orange_county'

    # urls

    search_url = 'https://cr.ocgov.com/recorderworks/'
    search_api=r'https://cr.ocgov.com/recorderworks/Presentors/AjaxPresentor.aspx'
    document_api=r'https://cr.ocgov.com/recorderworks/Presentors/DetailsPresentor.aspx'

    # request parameters

    generic_headers={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:65.0) Gecko/20100101 Firefox/65.0',
                     'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'}
    search_param={
        'ERetrievalGroup':1,
        'SearchMode':4,
        'IsNewSearch':'true'
    }

    document_param=dict(
        ImgIsPCOR=False,
        ImgIsDTT = False,
        ImgIsOBIndex = False,
        ImgIsOBDocImage = False,
        OBBookTab='',
        OBBookSeq='',
        OBIndexPage='',
        OBImageFileName='',
        OBImagePageCount='',
        OBDocImageBook='',
        OBDocImagePage='',
        FromBasket = False,
        FitToSize = False,
        isNextDifItem = 1,
        isPrevDifItem = 1,
        BookFirstPage = 0,
        ERetrievalGroup = 1,
        IsNewSearch = True
    )

    # regex tools

    get_page=regex.compile(r'(?<=OnPage\(\')\d*?(?=\'\,\'\.booking)',regex.IGNORECASE)
    get_document_body=regex.compile(r'(?<=showDetails\(\')[^\']*?(?=\'\,)',regex.IGNORECASE)

    # css syntax

    pages_css='tr>td.boldLinkColor::attr(onclick)'
    document_css='td[id*=docLinkTD]::attr(onclick)'

    # custom options

    time_chunk = 7

    def __init__(self,*args,**kwargs):
        self.start_date=datetime.strptime(kwargs['start_date'],'%m/%d/%Y')
        self.end_date=datetime.strptime(kwargs['end_date'],'%m/%d/%Y')

    def start_requests(self):
        start_date=self.start_date
        index=0
        while start_date<=self.end_date:
            # Set end of time chunk
            end_date=min(self.end_date,start_date+timedelta(days=self.time_chunk))

            # Do something
            search_param=self.search_param.copy()
            search_param.update({
                'FromDate': start_date.strftime('%m/%d/%Y'),
                'ToDate': end_date.strftime('%m/%d/%Y'),
            })
            yield scrapy.Request(
                url=self.search_url,headers=self.generic_headers,callback=self.parse_chunk,
                meta={'cookiejar':index,'search_param':search_param.copy()},dont_filter=True
            )

            # Increase time chunk
            start_date=end_date+timedelta(days=1)
            index+=1

    # parse chunk each search chunk, we need to chunk the target search period into 7 day chunk because server require so
    def parse_chunk(self,response):
        search_param=response.meta['search_param']
        yield scrapy.Request(
            url=self.search_api,method='POST',headers=self.generic_headers,body=urlencode(search_param),
            callback=self.parse_page,meta={'cookiejar':response.meta['cookiejar'],'search_param':search_param.copy()}
        )

    # parse each page of chunk
    def parse_page(self,response):
        search_param=response.meta['search_param']
        del search_param['IsNewSearch']

        pages=response.css(self.pages_css).extract()
        if not pages:return

        yield from self.parse_general(response)

        last_page = int(self.get_page.search(pages[len(pages) - 1]).group())
        for page in range(1,last_page):
            page+=1
            search_param['PageNum']=page
            yield scrapy.Request(
                url=self.search_api, method='POST', headers=self.generic_headers, body=urlencode(search_param),
                callback=self.parse_general, meta={'cookiejar': response.meta['cookiejar']}
            )


    # parse each document in page
    def parse_general(self,response):
        documents=response.css(self.document_css).extract()
        for document in documents:
            document_param=self.get_document_body.search(document).group()+'&isNextDifItem=1&isPrevDifItem=1'
            yield scrapy.Request(url=self.document_api,method='POST',headers=self.generic_headers,body=document_param,callback=self.parse_detail,meta={'cookiejar':response.meta['cookiejar']})

    # parse each document to yield item
    def parse_detail(self,response):
        item=dict()

        item['Document Number']=response.css('#DocumentSpinner1_docNumber::text').extract_first()
        if item['Document Number']:
            item['Document Number']=item['Document Number'].strip()

        item['Number of Pages']=response.css('.detailsData::text').extract()[0]
        item['Recording Date'] = response.css('.detailsData::text').extract()[1]

        document_types=response.css('#DocumentTitlesList>.marginedTable>tr').extract()
        for type in document_types:
            type_select=Selector(text=type)
            checked=type_select.css('input[checked=checked]').extract_first()
            if not checked:continue
            item['Document Type']=type_select.css('td:nth-child(2)::text').extract_first()
            if item['Document Type']:
                item['Document Type']=item['Document Type'].strip()

        item['Grantors']=','.join(response.css('#Grantors>table.displayBlock>tr>td::text').extract())
        item['Grantees']=','.join(response.css('#Grantees>table>tr>td::text').extract())

        yield item








