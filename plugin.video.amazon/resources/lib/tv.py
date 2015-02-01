#!/usr/bin/env python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
from BeautifulSoup import BeautifulStoneSoup
from BeautifulSoup import BeautifulSoup
import os.path
import re
import urllib
import xbmcplugin
import xbmc
import xbmcgui
import resources.lib.common as common
import appfeed
import urlparse
import string
try:
    from sqlite3 import dbapi2 as sqlite
except:
    from pysqlite2 import dbapi2 as sqlite
import xbmcaddon

################################ TV db
MAX = int(common.addon.getSetting("tv_perpage"))
MAX_MOV = int(common.addon.getSetting("mov_perpage"))
EPI_TOTAL = common.addon.getSetting("EpisodesTotal")
if EPI_TOTAL == '': EPI_TOTAL = '17000'
EPI_TOTAL = int(EPI_TOTAL)

Dialog = xbmcgui.Dialog()
DialogPG = xbmcgui.DialogProgress()

def createTVdb():
    c = tvDB.cursor()
    c.execute('''CREATE TABLE shows(
                 asin TEXT UNIQUE,
                 asin2 TEXT UNIQUE,
                 feed TEXT,
                 seriestitle TEXT,
                 poster TEXT,
                 plot TEXT,
                 network TEXT,
                 mpaa TEXT,
                 genres TEXT,
                 actors TEXT,
                 airdate TEXT,
                 year INTEGER,
                 stars float,
                 votes TEXT,
                 seasontotal INTEGER,
                 episodetotal INTEGER,
                 watched INTEGER,
                 unwatched INTEGER,
                 isHD BOOLEAN,
                 isprime BOOLEAN,
                 audio INTEGER,
                 TVDBbanner TEXT,
                 TVDBposter TEXT,
                 fanart TEXT,
                 TVDB_ID TEXT,
                 PRIMARY KEY(asin,seriestitle)
                 );''')
    c.execute('''CREATE TABLE seasons(
                 asin TEXT UNIQUE,
                 seriesasin TEXT,
                 fanart TEXT,
                 poster TEXT,
                 season INTEGER,
                 seriestitle TEXT,
                 plot TEXT,
                 actors TEXT,
                 network TEXT,
                 mpaa TEXT,
                 genres TEXT,
                 airdate TEXT,
                 year INTEGER,
                 stars float,
                 votes TEXT,
                 episodetotal INTEGER,
                 audio INTEGER,
                 unwatched INTEGER,
                 isHD BOOLEAN,
                 isprime BOOLEAN,
                 PRIMARY KEY(asin,seriestitle,season,isHD),
                 FOREIGN KEY(seriestitle) REFERENCES shows(seriestitle)
                 );''')
    c.execute('''create table episodes(
                 asin TEXT UNIQUE,
                 seasonasin TEXT,
                 seriesasin TEXT,
                 seriestitle TEXT,
                 season INTEGER,
                 episode INTEGER,
                 poster TEXT,
                 mpaa TEXT,
                 actors TEXT,
                 genres TEXT,
                 episodetitle TEXT,
                 studio TEXT,
                 stars float,
                 votes TEXT,
                 fanart TEXT,
                 plot TEXT,
                 airdate TEXT,
                 year INTEGER,
                 runtime TEXT,
                 isHD BOOLEAN,
                 isprime BOOLEAN,
                 isAdult BOOLEAN,
                 audio INTEGER,
                 PRIMARY KEY(asin,seriestitle,season,episode,episodetitle,isHD),
                 FOREIGN KEY(seriestitle,season) REFERENCES seasons(seriestitle,season)
                 );''')
    tvDB.commit()
    c.close()

def loadTVShowdb(actorfilter=False,mpaafilter=False,genrefilter=False,creatorfilter=False,networkfilter=False,yearfilter=False,watchedfilter=False,favorfilter=False,alphafilter=False,asinfilter=False, isprime=True):
    c = tvDB.cursor()
    if genrefilter:
        genrefilter = '%'+genrefilter+'%'
        return c.execute('select distinct * from shows where isprime = (?) and genres like (?)', (isprime,genrefilter))
    elif actorfilter:
        return c.execute('select distinct * from shows where isprime = (?) and actors like (?)', (isprime,actorfilter))
    elif mpaafilter:
        return c.execute('select distinct * from shows where isprime = (?) and mpaa = (?)', (isprime,mpaafilter))
    elif creatorfilter:
        return c.execute('select distinct * from shows where isprime = (?) and creator = (?)', (isprime,creatorfilter))
    elif networkfilter:
        return c.execute('select distinct * from shows where isprime = (?) and network = (?)', (isprime,networkfilter))
    elif yearfilter:    
        return c.execute('select distinct * from shows where isprime = (?) and year = (?)', (isprime,int(yearfilter)))
    elif favorfilter:
        return c.execute('select distinct * from shows where isprime = (?) and favor = (?)', (isprime,favorfilter)) 
    elif alphafilter:
        return c.execute('select distinct * from shows where isprime = (?) and seriestitle like (?)', (isprime,alphafilter)) 
    elif asinfilter:
        asinfilter = '%' + asinfilter + '%'
        return c.execute('select distinct * from shows where isprime = (?) and asin like (?)', (isprime,asinfilter)) 
    else:
        return c.execute('select distinct * from shows where isprime = (?)', (isprime,))

def loadTVSeasonsdb(seriestitle,isprime=True):
    c = tvDB.cursor()
    return c.execute('select distinct * from seasons where isprime = (?) and seriesasin = (?)', (isprime,seriestitle))

def loadTVEpisodesdb(seriestitle,isprime=True):
    c = tvDB.cursor()
    return c.execute('select distinct * from episodes where isprime = (?) and seasonasin = (?) order by episode', (isprime,seriestitle))

def getShowTypes(col):
    c = tvDB.cursor()
    items = c.execute('select distinct %s from shows' % col)
    list = []
    lowlist = []
    for data in items:
        if data and data[0] <> None:
            data = data[0]
            if type(data) == type(str()):
                if 'genres' in col: data = data.decode('utf-8').encode('utf-8').split('/')
                else: data = data.decode('utf-8').encode('utf-8').split(',')
                for item in data:
                    item = item.strip()
                    if item.lower() not in lowlist and item <> '' and item <> 0 and item <> 'Inc.' and item <> 'LLC.':
                        list.append(item)
                        lowlist.append(item.lower())
            else:
                list.append(str(data))
    c.close()
    return list

def getPoster(seriestitle):
    c = tvDB.cursor()
    data = c.execute('select distinct poster from seasons where seriestitle = (?)', (seriestitle,)).fetchone()
    return data[0]

def fixHDshows():
    c = tvDB.cursor()
    c.execute("update shows set isHD=?", (False,))
    HDseasons = c.execute('select distinct seriestitle from seasons where isHD = (?)', (True,)).fetchall()
    for series in HDseasons:
        c.execute("update shows set isHD=? where seriestitle=?", (True,series[0]))
    tvDB.commit()
    c.close()
    
def fixGenres():
    c = tvDB.cursor()
    seasons = c.execute('select distinct seriestitle,genres from seasons where genres is not null').fetchall()
    for series,genres in seasons:
        c.execute("update seasons set genres=? where seriestitle=? and genres is null", (genres,series))
        c.execute("update shows set genres=? where seriestitle=? and genres is null", (genres,series))
    tvDB.commit()
    c.close()

def updateEpisodes():
    c = tvDB.cursor()
    shows = c.execute('select distinct asin from shows where episodetotal is 0').fetchall()
    for asin in shows:
        asinn = asin[0]
        nums = 0
        for sasin in asinn.split(','):
            nums += int((c.execute("select count(*) from episodes where seriesasin like ?", (sasin,)).fetchone())[0])
        c.execute("update shows set episodetotal=? where asin=?", (nums,asinn))
    tvDB.commit()
    c.close()
    
def fixYears():
    c = tvDB.cursor()
    seasons = c.execute('select seasonasin,year,season from episodes where year is not null order by year desc').fetchall()
    for asin,year,season in seasons:
        asin = '%' + asin + '%'
        c.execute("update seasons set year=? where season=? and asin like ?", (year,season,asin))
    seasons = c.execute('select seriesasin,year from seasons where year is not null order by year desc').fetchall()
    for asin,year in seasons:
        asin = '%' + asin + '%'
        c.execute("update shows set year=? where asin like ?", (year,asin))
    tvDB.commit()
    c.close()
    
def fixDBLShows():
    c = tvDB.cursor()
    allseries = []
    for asin,seriestitle in c.execute('select asin,seriestitle from shows').fetchall():
        flttitle = cleanTitle(seriestitle)
        addlist = True
        index = 0
        for asinlist,titlelist,fltlist in allseries:
            if flttitle == fltlist:
                allseries.pop(index)
                allseries.insert(index, [asinlist + ',' + asin,titlelist,fltlist])
                c.execute('delete from shows where seriestitle = (?) and asin = (?)', (seriestitle,asin))
                addlist = False
            index += 1
        if addlist: allseries.append([asin,seriestitle,flttitle])
    for asinlist,titlelist,fltlist in allseries: 
        c.execute("update shows set asin = (?) where seriestitle = (?)", (asinlist, titlelist))
    tvDB.commit()
    c.close()
    
def fixStars():
    c = tvDB.cursor()
    series = c.execute('select seriestitle from shows where votes is 0').fetchall()
    for title in series:
        title = title[0]
        stars = c.execute('select avg(stars) from seasons where seriestitle like ? and votes is not 0', (title,)).fetchone()[0]
        if stars: c.execute('update shows set stars = (?) where seriestitle = (?)', (stars, title))
    tvDB.commit()
    c.close()
    
def cleanTitle(content):
    content = content.replace(' und ','').lower()
    invalid_chars = "?!.:&,;' "
    return ''.join(c for c in content if c not in invalid_chars)

def addEpisodedb(episodedata):
    c = tvDB.cursor()
    c.execute('insert or ignore into episodes values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)', episodedata)
    tvDB.commit()
    c.close()
    
def addSeasondb(seasondata):
    c = tvDB.cursor()
    c.execute('insert or ignore into seasons values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)', seasondata)
    tvDB.commit()
    c.close()

def addShowdb(showdata):
    c = tvDB.cursor()
    c.execute('insert or ignore into shows values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)', showdata)
    tvDB.commit()
    c.close()

def lookupTVdb(value, rvalue='distinct *', tbl='episodes', name='asin', single=True, exact=False):
    c = tvDB.cursor()
    sqlstring = 'select %s from %s where %s ' % (rvalue, tbl, name)
    retlen = len(rvalue.split(','))
    if not exact:
        value = '%' + value + '%'
        sqlstring += 'like (?)'
    else:
        sqlstring += '= (?)'
    if c.execute(sqlstring, (value,)).fetchall():
        result = c.execute(sqlstring, (value,)).fetchall()
        if single:
            if len(result[0]) > 1:
                return result[0]
            return result[0][0]
        else:
            return result
    if (retlen < 2) and (single):
        return None
    return (None,) * retlen

def countDB(tbl):
    c = tvDB.cursor()
    return len(c.execute('select * from %s' % tbl).fetchall())
    
def delfromTVdb():
    asins = common.args.asins
    title = common.args.title
    table = common.args.table
    id = 30166
    if table == 'seasons': id = 30155

    if Dialog.yesno(common.getString(id), common.getString(30156) % title):
        delasins = []
        if table == 'seasons':
            delasins.append(asins)
        else:
            for asin in asins.split(','):
                for item in lookupTVdb(asin, rvalue='asin', tbl='seasons', name='seriesasin', single=False):
                    if item: delasins += (item)
        UpdateDialog(0, 0, 0, *deleteremoved(delasins))
        
def deleteremoved(asins):
    c = tvDB.cursor()
    delShows = 0
    delSeasons = 0
    delEpisodes = 0
    for item in asins:
        for seasonasin in item.split(','):
            title, season = lookupTVdb(seasonasin, rvalue='seriestitle, season', tbl='seasons', name='asin')
            if title and season:
                delEpisodes += c.execute('delete from episodes where seriestitle = (?) and season = (?)', (title, season)).rowcount
                delSeasons += c.execute('delete from seasons where seriestitle = (?) and season = (?)', (title, season)).rowcount
                if not lookupTVdb(title, rvalue='asin', tbl='seasons', name='seriestitle'):
                    delShows += c.execute('delete from shows where seriestitle = (?)', (title,)).rowcount
    tvDB.commit()
    c.close()
    xbmc.executebuiltin("XBMC.Container.Refresh")
    return delShows, delSeasons, delEpisodes

def rebuildTVdb():
    c = tvDB.cursor()
    c.execute('drop table if exists shows')
    c.execute('drop table if exists seasons')
    c.execute('drop table if exists episodes')
    c.close()
    createTVdb()

def getTVdbAsins(table,col=False,list=False):
    c = tvDB.cursor()
    content = ''
    if list:
        content = []
    sqlstring = 'select asin from ' + table
    if col:
         sqlstring += ' where %s = (1)' % col
    for item in c.execute(sqlstring).fetchall():
        if list:
            content.append(','.join(item))
        else:
            content += ','.join(item) + ','
    return content
    
def addTVdb():
    page = 1
    endIndex = 0
    goAhead = 1
    SERIES_COUNT = 0
    SEASON_COUNT = 0
    EPISODE_COUNT = 0
    print countDB('episodes')
    if common.args.url == 'u':
        DialogPG.create(common.getString(30135))
        ALL_SEASONS_ASINS = getTVdbAsins('seasons', list=True)
        ALL_SERIES_ASINS = getTVdbAsins('shows')
    else:
        if not Dialog.yesno(common.getString(30136), common.getString(30137), common.getString(30138) % '30'):
            return
        DialogPG.create(common.getString(30130))
        rebuildTVdb()
        ALL_SERIES_ASINS = ''
        ALL_SEASONS_ASINS = []
    DialogPG.update(0,common.getString(30131))
    
    while goAhead == 1:
        json = appfeed.getList('TVSeason', endIndex, NumberOfResults=MAX)
        titles = json['message']['body']['titles']
        newtitles = []
        if titles:
            SERIES_ASINS = ''
            EPISODE_ASINS = []
            EPISODE_NUM = []
            result = len(titles)
            for title in titles:
                if (DialogPG.iscanceled()):
                    goAhead = -1
                    break
                SEASONS_ASIN = title['titleId']
                listpos = [i for i, j in enumerate(ALL_SEASONS_ASINS) if SEASONS_ASIN in j]
                if listpos == []:
                    if title['ancestorTitles']:
                        SERIES_KEY = title['ancestorTitles'][0]['titleId']
                    else:
                        SERIES_KEY = title['titleId']
                    if SERIES_KEY not in ALL_SERIES_ASINS and 'bbl test' not in title['title'].lower():
                        SERIES_COUNT += 1
                        SERIES_ASINS += SERIES_KEY+','
                        ALL_SERIES_ASINS += SERIES_KEY+','
                    season_size = int(title['childTitles'][0]['size'])
                    if season_size < 1:
                        season_size = MAX_MOV
                    parsed = urlparse.urlparse(title['childTitles'][0]['feedUrl'])
                    EPISODE_ASINS.append(urlparse.parse_qs(parsed.query)['SeasonASIN'])
                    EPISODE_NUM.append(season_size)
                    newtitles.append(title)
                else:
                    while listpos != []:
                        del ALL_SEASONS_ASINS[listpos[0]]
                        listpos = [i for i, j in enumerate(ALL_SEASONS_ASINS) if SEASONS_ASIN in j]
            SEASON_COUNT += ASIN_ADD(newtitles)
            del titles, newtitles
            if SERIES_ASINS <> '':
                ASIN_ADD(0, asins=SERIES_ASINS)
            if (common.args.url == 'u') and (SEASON_COUNT == 0):
                DialogPG.update(0, common.getString(30122).replace("%s",str(page)))
            else:
                DialogPG.update(int(EPISODE_COUNT*100.0/EPI_TOTAL), common.getString(30132) % SERIES_COUNT, common.getString(30133) % SEASON_COUNT,common.getString(30134) % EPISODE_COUNT)
            goAheadepi = 1
            episodes = 0
            AsinList = ''
            EPISODE_NUM.append(MAX_MOV + 1)
            for index, item in enumerate(EPISODE_ASINS):
                episodes += EPISODE_NUM[index]
                AsinList += ','.join(item) + ','
                if (episodes + EPISODE_NUM[index+1]) > MAX_MOV:
                    json = appfeed.getList('TVEpisode', 0, NumberOfResults=MAX_MOV, AsinList=AsinList)
                    titles = json['message']['body']['titles']
                    if titles:
                        EPISODE_COUNT += ASIN_ADD(titles)
                    else:
                        goAheadepi = -1
                    if (DialogPG.iscanceled()):
                        goAheadepi = -1
                        goAhead = -1
                        break
                    episodes = 0
                    AsinList = ''
                    if (common.args.url == 'u') and (SEASON_COUNT == 0):
                        DialogPG.update(0, common.getString(30122).replace("%s",str(page)))
                    else:
                        DialogPG.update(int(EPISODE_COUNT*100.0/EPI_TOTAL), common.getString(30132) % SERIES_COUNT, common.getString(30133) % SEASON_COUNT,common.getString(30134) % EPISODE_COUNT)
                    del titles
            endIndex+=result
        else:
            goAhead = 0
        page+=1
    if goAhead == 0:
        common.addon.setSetting("EpisodesTotal",str(countDB('episodes')))
    fixDBLShows()
    fixYears()
    fixStars()
    fixHDshows()
    updateEpisodes()
    DialogPG.close()
    print ALL_SEASONS_ASINS
    delShows, delSeasons, delEpisodes = deleteremoved(ALL_SEASONS_ASINS)
    UpdateDialog(SERIES_COUNT, SEASON_COUNT, EPISODE_COUNT, delShows, delSeasons, delEpisodes)
    
def UpdateDialog(SERIES_COUNT, SEASON_COUNT, EPISODE_COUNT, delShows, delSeasons, delEpisodes):
    line1 = ''
    line2 = ''
    line3 = ''
    if SERIES_COUNT:
        line1 += '%s %s' % (common.getString(30132) % SERIES_COUNT, common.getString(30124))
        if delShows: line1 += ', %s %s' % (delShows, common.getString(30125))
    if (delShows) and (not SERIES_COUNT):
        line1 += '%s %s' % (common.getString(30132) % delShows, common.getString(30125))
    if SEASON_COUNT:
        line2 += '%s %s' % (common.getString(30133) % SEASON_COUNT, common.getString(30124))
        if delSeasons: line2 += ', %s %s' % (delSeasons, common.getString(30125))
    if (delSeasons) and (not SEASON_COUNT):
        line2 += '%s %s' % (common.getString(30133) % delSeasons, common.getString(30125))
    if EPISODE_COUNT:
        line3 += '%s %s' % (common.getString(30134) % EPISODE_COUNT, common.getString(30124))
        if delEpisodes: line3 += ', %s %s' % (delEpisodes, common.getString(30125))
    if (delEpisodes) and (not EPISODE_COUNT):
        line3 += '%s %s' % (common.getString(30134) % delEpisodes, common.getString(30125))
    if line1 + line2 + line3 == '': line2 = common.getString(30127)
    Dialog.ok(common.getString(30126), line1, line2, line3)
    
def ASIN_ADD(titles,asins=False,url=False,isPrime=True,isHD=False,single=False):
    if asins:
        titles = appfeed.ASIN_LOOKUP(asins)['message']['body']['titles']
    count = 0
    for title in titles:
        poster = plot = premiered = year = studio = mpaa = fanart = None
        actors = genres = stars = votes = seriesasin = runtime = None
        seasontotal = episodetotal = episode = 0
        isAdult = False
        if asins:
            contentType = 'SERIES'
        else:
            contentType = title['contentType']

        count+=1
        asin, isHD, isPrime, audio = common.GET_ASINS(title)
        if title['formats'][0].has_key('images'):
            try:
                thumbnailUrl = title['formats'][0]['images'][0]['uri']
                thumbnailFilename = thumbnailUrl.split('/')[-1]
                thumbnailBase = thumbnailUrl.replace(thumbnailFilename,'')
                poster = thumbnailBase+thumbnailFilename.split('.')[0]+'.jpg'
            except: pass
        if title.has_key('synopsis'):
            plot = title['synopsis']
        if title.has_key('releaseOrFirstAiringDate'):
            premiered = title['releaseOrFirstAiringDate']['valueFormatted'].split('T')[0]
            year = int(premiered.split('-')[0])
        if title.has_key('studioOrNetwork'):
            studio = title['studioOrNetwork']
        if title.has_key('regulatoryRating'):
            if title['regulatoryRating'] == 'not_checked': mpaa = common.getString(30171)
            else: mpaa = common.getString(30170) + title['regulatoryRating']
        if title.has_key('starringCast'):
            actors = title['starringCast']
        if title.has_key('genres'):
            genres = ' / '.join(title['genres']).replace('_', ' & ').replace('Musikfilm & Tanz', 'Musikfilm, Tanz')
        if title.has_key('customerReviewCollection'):
            stars = float(title['customerReviewCollection']['customerReviewSummary']['averageOverallRating'])*2
            votes = str(title['customerReviewCollection']['customerReviewSummary']['totalReviewCount'])
        elif title.has_key('amazonRating'):
            if title['amazonRating'].has_key('rating'): stars = float(title['amazonRating']['rating'])*2
            if title['amazonRating'].has_key('count'): votes = str(title['amazonRating']['count'])                
        if title.has_key('heroUrl'):
            fanart = title['heroUrl']
            
        if contentType == 'SERIES':
            seriestitle = title['title']
            if title.has_key('childTitles'):
                seasontotal = title['childTitles'][0]['size']
            showdata = [common.cleanData(x) for x in [asin,None,None,seriestitle,poster,plot,studio,mpaa,genres,actors,premiered,year,stars,votes,seasontotal,0,False,0,isHD,isPrime,audio,None,None,fanart,None]]
            addShowdb(showdata)
            if single:
                return asin,ASINLIST
        elif contentType == 'SEASON':
            season = title['number']
            if title['ancestorTitles']:
                try:
                    seriestitle = title['ancestorTitles'][0]['title']
                    seriesasin = title['ancestorTitles'][0]['titleId']
                except: pass
            else:
                seriesasin = asin.split(',')[0]
                seriestitle = title['title']
            if title.has_key('childTitles'):
                episodetotal = title['childTitles'][0]['size']
            seasondata = [common.cleanData(x) for x in [asin,seriesasin,fanart,poster,season,seriestitle,plot,actors,studio,mpaa,genres,premiered,year,stars,votes,episodetotal,audio,0,isHD,isPrime]]
            addSeasondb(seasondata)
        elif contentType == 'EPISODE':
            episodetitle = title['title']
            if title.has_key('ancestorTitles'):
                for content in title['ancestorTitles']:
                    if content['contentType'] == 'SERIES':
                        if content.has_key('titleId'): seriesasin = content['titleId']
                        if content.has_key('title'): seriestitle = content['title']
                    elif content['contentType'] == 'SEASON':
                        if content.has_key('number'): season = content['number']
                        if content.has_key('titleId'): seasonasin = content['titleId']
                        if content.has_key('title'): seasontitle = content['title']
                if not seriesasin:
                    seriesasin = seasonasin
                    seriestitle = seasontitle                        
            if title.has_key('number'):
                episode = title['number']
            if title.has_key('runtime'):
                runtime = str(title['runtime']['valueMillis']/60000)
            if title.has_key('restrictions'):
                for rest in title['restrictions']:
                    if rest['action'] == 'playback':
                        if rest['type'] == 'ageVerificationRequired': isAdult = True
            episodedata = [common.cleanData(x) for x in [asin,seasonasin,seriesasin,seriestitle,season,episode,poster,mpaa,actors,genres,episodetitle,studio,stars,votes,fanart,plot,premiered,year,runtime,isHD,isPrime,isAdult,audio]]
            addEpisodedb(episodedata)
    return count
    
tvDBfile = os.path.join(common.dbpath, 'tv.db')
if not os.path.exists(tvDBfile):
    tvDB = sqlite.connect(tvDBfile)
    tvDB.text_factory = str
    createTVdb()
else:
    tvDB = sqlite.connect(tvDBfile)
    tvDB.text_factory = str
