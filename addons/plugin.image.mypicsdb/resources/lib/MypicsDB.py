# -*- coding: utf8 -*-
"""
Todo :
* ability to remove a file from database
* use smb file access to browse smb share pictures:
    http://sourceforge.net/projects/pysmb/


"""
import os,sys #,re
from os.path import join
#from urllib import unquote_plus
from traceback import print_exc

import  xbmc, xbmcgui
import common


from time import strftime,strptime

#base de donnée SQLITE
try:
    from sqlite3 import dbapi2 as sqlite
except:
    from pysqlite2 import dbapi2 as sqlite
    pass


home = common.getaddon_path()

#these few lines are taken from AppleMovieTrailers script
# Shared resources
BASE_RESOURCE_PATH = join( home, "resources" )
DATA_PATH = common.getaddon_info('profile')
DB_PATH = xbmc.translatePath( "special://database/")
sys.path.append( os.path.join( BASE_RESOURCE_PATH, "lib" ) )
# append the proper platforms folder to our path, xbox is the same as win32
env = ( os.environ.get( "OS", "win32" ), "win32", )[ os.environ.get( "OS", "win32" ) == "xbox" ]
sys.path.append( os.path.join( BASE_RESOURCE_PATH, "platform_libraries", env ) )


DB_VERSION19 = '1.9.12'
DB_VERSION201 = '2.0.1'
DB_VERSION = '2.1.1'

global pictureDB
pictureDB = join(DB_PATH,"MyPictures.db")
sys_enc = sys.getfilesystemencoding()

lists_separator = "||"

class MyPictureDB(Exception):
    pass


def version_table():
    #table 'Version'
    conn = sqlite.connect(pictureDB)
    conn.text_factory = unicode #sqlite.OptimizedUnicode
    cn=conn.cursor()
    
    # Test Version of DB
    try:
        strVersion = Request("Select strVersion from DBVersion")[0][0]
    except:
        strVersion = '1.0.0'

    common.log("MPDB.version_table", "MyPicsDB database version is %s"%str(strVersion) ) 

    # version of DB is greater/equal than 1.9.0 but less then 2.0.1
    if common.check_version(strVersion, DB_VERSION201)>0 and common.check_version(strVersion, DB_VERSION19) <=0:
        common.log("MPDB.version_table", "MyPicsDB database with version %s will be updated to version %s"%(str(strVersion),str(DB_VERSION)) ) 
        version_201_tables(pictureDB)
        # update tags for new introduced yyyy-mm  tag
        update_yyyy_mm_tags()
        
    # version of DB is less then 1.9.0
    elif common.check_version(strVersion, DB_VERSION19) >0:
        dialog = xbmcgui.Dialog()
        dialog.ok(common.getstring(30000).encode("utf8"), "Database will be updated", "You must re-scan your folders")
        common.log("MPDB.Versiversion_tableonTable", "MyPicsDB database will be updated", xbmc.LOGNOTICE )
        make_new_base(pictureDB, True)
        #VersionTable()
        
    # version of DB is less then current version
    elif common.check_version(strVersion, DB_VERSION)>0:
        # update tags for new introduced yyyy-mm  tag
        common.log("MPDB.version_table", "MyPicsDB database will be updated to version %s. New YYYY-MM tags will be inserted."%str(DB_VERSION), xbmc.LOGNOTICE )
        update_yyyy_mm_tags()
        version_211_tables(pictureDB)         
        cn.execute("update DBVersion set strVersion = '"+DB_VERSION+"'")
        conn.commit()
    else:
        common.log("MPDB.version_table", "MyPicsDB database contains already current schema" )
        
    cn.close()

# new tag type YYYY-MM in version 2.10
def update_yyyy_mm_tags():   
    conn = sqlite.connect(pictureDB)
    cn=conn.cursor()
    dictionnary = {}
    common.show_notification(common.getstring(30000), 'DB-Update', 2000)
    cn.execute("SELECT idFile, strFilename, strPath, ImageDateTime FROM files")
    rows = [row for row in cn]
    for row in rows:
        dictionnary['YYYY-MM'] = row[3][:7]
        try:
            tags_insert(conn, cn, row[0], row[1], row[2], dictionnary)
            common.log( 'MPDB.update_yyyy_mm_tags()', 'Tag YYYY-MM with value %s inserted for "%s"'%(dictionnary['YYYY-MM'], row[1]) )
        except:
            common.log( 'MPDB.update_yyyy_mm_tags()', 'Tag YYYY-MM with value %s NOT inserted for "%s"'%(dictionnary['YYYY-MM'], row[1]) )
            
    conn.commit()
    cn.close()
    return True

def version_211_tables(DBpath):
    conn = sqlite.connect(DBpath)
    cn=conn.cursor()    
    try:
        cn.execute("drop table FilterWizard ")
        cn.execute("drop table FilterWizardItems ")
    except:
        pass
       
    cn.close()
    version_201_tables(DBpath)
        
# new tables in version 2.0.1
def version_201_tables(DBpath):
    #table 'FilterWizard'
    conn = sqlite.connect(DBpath)
    cn=conn.cursor()    
    try:
        cn.execute("""create table FilterWizard (pkFilter integer primary key, strFilterName text unique, bMatchAll integer, StartDate date, EndDate date)""")
    except Exception,msg:
        if str(msg).find("already exists") > -1:
            pass
        else:
            common.log("MPDB.version_201_tables", "CREATE TABLE FilterWizard ...", xbmc.LOGERROR )
            common.log("MPDB.version_201_tables", "%s - %s"%(Exception,msg), xbmc.LOGERROR )

    #table 'FilterWizardItems'
    try:
        cn.execute("""create table FilterWizardItems (idItems integer primary key, fkFilter integer, strItem, nState integer, FOREIGN KEY(fkFilter) REFERENCES FilterWizard(pkFilter))""")
    except Exception,msg:
        if str(msg).find("already exists") > -1:
            pass
        else:
            common.log("MPDB.version_201_tables", "CREATE TABLE FilterWizardItems ...", xbmc.LOGERROR )
            common.log("MPDB.version_201_tables", "%s - %s"%(Exception,msg), xbmc.LOGERROR )
            
    cn.execute("update DBVersion set strVersion = '"+DB_VERSION+"'")
    conn.commit()            
    cn.close()

    
def make_new_base(DBpath,ecrase=True):
##    if not(isfile(DBpath)):
##        f=open("DBpath","w")
##        f.close()
    common.log("MPDB.make_new_base >> Picture database", "%s"%DBpath)
    conn = sqlite.connect(DBpath)
    cn=conn.cursor()
    if ecrase:
        #drop table
        for table in ['FilterWizard', 'FilterWizardItems', 'Persons', 'PersonsInFiles', 'tags', 'TagContent', 'TagContents', 'TagsInFiles', 'TagTypes',"files","keywords","folders","KeywordsInFiles","Collections","FilesInCollections","Periodes","CategoriesInFiles","Categories","SupplementalCategoriesInFiles","SupplementalCategories","CitiesInFiles","Cities","CountriesInFiles","Countries","DBVersion"]:
            common.log("MPDB.make_new_base >> Dropping table", "%s"%table)
            try:
                cn.execute("""DROP TABLE %s"""%table)
            except Exception,msg:
                common.log("MPDB.make_new_base", "DROP TABLE %s"%table, xbmc.LOGERROR )
                common.log("MPDB.make_new_base", "%s - %s"%(Exception,msg), xbmc.LOGERROR )

    # table: version
    try:
        cn.execute("""CREATE TABLE DBVersion ( strVersion text)""")
    except Exception,msg:
        if str(msg).find("already exists") > -1:
            pass
        else: #sinon on imprime l'exception levée pour la traiter
            common.log("MPDB.make_new_base", "CREATE TABLE files ...", xbmc.LOGERROR )
            common.log("MPDB.make_new_base", "%s - %s"%(Exception,msg), xbmc.LOGERROR )    

    try:
        cn.execute("insert into DBVersion values('"+DB_VERSION+"')")
        conn.commit()
    except:
        pass
        
    #table 'files'
    try:
        cn.execute("""CREATE TABLE files ( idFile integer primary key, idFolder integer, strPath text, strFilename text, ftype text, DateAdded DATETIME, Thumb text,  ImageRating text, ImageDateTime DATETIME, Sha text, CONSTRAINT UNI_FILE UNIQUE (strPath,strFilename))""")
    except Exception,msg:
        if str(msg).find("already exists") > -1:
            pass
        else: #sinon on imprime l'exception levée pour la traiter
            common.log("MPDB.make_new_base", "CREATE TABLE files ...", xbmc.LOGERROR )
            common.log("MPDB.make_new_base", "%s - %s"%(Exception,msg), xbmc.LOGERROR )

    #table 'folders'
    try:
        cn.execute("""CREATE TABLE folders (idFolder INTEGER primary key not null, FolderName TEXT, ParentFolder INTEGER, FullPath TEXT UNIQUE, HasPics INTEGER)""")
    except Exception,msg:
        if str(msg).find("already exists") > -1:
            #cette exception survient lorsque la table existe déjà.
            #   elle n'est pas une erreur, on la passe
            pass
        else: #sinon on imprime l'exception levée pour la traiter
            common.log("MPDB.make_new_base", "CREATE TABLE folders ...", xbmc.LOGERROR )
            common.log("MPDB.make_new_base", "%s - %s"%(Exception,msg), xbmc.LOGERROR )
    #table 'Collections'
    try:
        cn.execute("""CREATE TABLE Collections (idCol INTEGER PRIMARY KEY, CollectionName TEXT UNIQUE)""")
    except Exception,msg:
        if str(msg).find("already exists") > -1:
            #cette exception survient lorsque la table existe déjà.
            #   elle n'est pas une erreur, on la passe
            pass
        else: #sinon on imprime l'exception levée pour la traiter
            common.log("MPDB.make_new_base", "CREATE TABLE Collections ...", xbmc.LOGERROR )
            common.log("MPDB.make_new_base", "%s - %s"%(Exception,msg), xbmc.LOGERROR )
    #table 'FilesInCollections'
    try:
        cn.execute("""CREATE TABLE FilesInCollections (idCol INTEGER NOT NULL, idFile INTEGER NOT NULL, Constraint UNI_COLLECTION UNIQUE (idCol,idFile))""")
    except Exception,msg:
        if str(msg).find("already exists") > -1:
            #cette exception survient lorsque la table existe déjà.
            #   elle n'est pas une erreur, on la passe
            pass
        else: #sinon on imprime l'exception levée pour la traiter
            common.log("MPDB.make_new_base", "CREATE TABLE FilesInCollections ...", xbmc.LOGERROR )
            common.log("MPDB.make_new_base", "%s - %s"%(Exception,msg), xbmc.LOGERROR )
    #table 'periodes'
    try:
        cn.execute("""CREATE TABLE periodes(idPeriode INTEGER  PRIMARY KEY NOT NULL, PeriodeName TEXT UNIQUE NOT NULL, DateStart DATETIME NOT NULL, DateEnd DATETIME NOT NULL, CONSTRAINT UNI_PERIODE UNIQUE (PeriodeName,DateStart,DateEnd) )""")
    except Exception,msg:
        if str(msg).find("already exists") > -1:
            #cette exception survient lorsque la table existe déjà.
            #   elle n'est pas une erreur, on la passe
            pass
        else: #sinon on imprime l'exception levée pour la traiter
            common.log("MPDB.make_new_base", "CREATE TABLE Periods ...", xbmc.LOGERROR )
            common.log("MPDB.make_new_base", "%s - %s"%(Exception,msg), xbmc.LOGERROR )
    #table 'Rootpaths'
    try:
        cn.execute("""CREATE TABLE Rootpaths (idRoot INTEGER PRIMARY KEY NOT NULL, Path TEXT UNIQUE NOT NULL, Recursive INTEGER NOT NULL, Remove INTEGER NOT NULL, Exclude INTEGER DEFAULT 0)""")
    except Exception,msg:
        if str(msg).find("already exists") > -1:
            #cette exception survient lorsque la table existe déjà.
            #   elle n'est pas une erreur, on la passe
            pass
        else: #sinon on imprime l'exception levée pour la traiter
            common.log("MPDB.make_new_base", "CREATE TABLE RootPaths ...", xbmc.LOGERROR )
            common.log("MPDB.make_new_base", "%s - %s"%(Exception,msg), xbmc.LOGERROR )


    #table 'TagTypes'
    try:
        cn.execute("""CREATE TABLE TagTypes (idTagType INTEGER NOT NULL primary key, TagType TEXT, TagTranslation TEXT, CONSTRAINT UNI_TAG UNIQUE(TagType) )""")
    except Exception,msg:
        if str(msg).find("already exists") > -1:
            pass
        else:
            common.log("MPDB.make_new_base", "CREATE TABLE TagTypes ...", xbmc.LOGERROR )
            common.log("MPDB.make_new_base", "%s - %s"%(Exception,msg), xbmc.LOGERROR )

    #table 'TagContent'
    try:
        cn.execute("""CREATE TABLE TagContents (idTagContent INTEGER NOT NULL primary key, idTagType INTEGER, TagContent TEXT, CONSTRAINT UNI_TAG UNIQUE(idTagType, TagContent) )""")
    except Exception,msg:
        if str(msg).find("already exists") > -1:
            pass
        else:
            common.log("MPDB.make_new_base", "CREATE TABLE Tags ...", xbmc.LOGERROR )
            common.log("MPDB.make_new_base", "%s - %s"%(Exception,msg), xbmc.LOGERROR )

    #table 'TagsInFiles'
    try:
        cn.execute("""CREATE TABLE TagsInFiles (idTagContent INTEGER NOT NULL, idFile INTEGER NOT NULL)""")
    except Exception,msg:
        if str(msg).find("already exists") > -1:
            pass
        else:
            common.log("MPDB.make_new_base", "CREATE TABLE TagsInFiles ...", xbmc.LOGERROR )
            common.log("MPDB.make_new_base", "%s - %s"%(Exception,msg), xbmc.LOGERROR )


    version_201_tables(DBpath)
    
    try:
        cn.execute("CREATE INDEX idxFilesInCollections1 ON FilesInCollections(idCol)")
    except Exception,msg:
        pass


    # Index creation for new tag tables
    try:
        cn.execute("CREATE INDEX idxTagTypes1 ON TagTypes(idTagType)")
    except Exception,msg:
        pass

    try:
        cn.execute("CREATE INDEX idxTagContent1 ON TagContents(idTagContent)")
    except Exception,msg:
        pass

    try:
        cn.execute("CREATE INDEX idxTagsInFiles1 ON TagsInFiles(idTagContent)")
        cn.execute("CREATE INDEX idxTagsInFiles2 ON TagsInFiles(idFile)")
    except Exception,msg:
        pass

    try:
        cn.execute("CREATE INDEX idxFolders1 ON Folders(idFolder)")
        cn.execute("CREATE INDEX idxFolders2 ON Folders(ParentFolder)")
    except Exception,msg:
        pass

    try:
        cn.execute("CREATE INDEX idxFiles1 ON Files(idFile, idFolder)")
        cn.execute("CREATE INDEX idxFilesInCollections ON FilesInCollections (idFile)")
    except Exception,msg:
        pass

    conn.commit()

    cn.close()
"""
columnList = []
def addColumn(table,colheader,formatstring="text"):
    global columnList
    key = table + '||' + colheader + '||' + formatstring
    try:
        columnList.index(key);
        return
    except:
        conn = sqlite.connect(pictureDB)
        cn=conn.cursor()
        try:
            cn.execute('ALTER TABLE %s ADD "%s" %s'%(table,colheader,formatstring))
        except Exception,msg:
            if not msg.args[0].startswith("duplicate column name"):
                common.log("MPDB.addColumn", 'EXCEPTION  %s,%s,%s'%(table,colheader,formatstring), xbmc.LOGERROR )
                common.log("MPDB.addColumn", "\t%s - %s"%(Exception,msg), xbmc.LOGERROR )

        conn.commit()
        cn.close()
        columnList.append(key)
"""

def cleanup_keywords():
    conn = sqlite.connect(pictureDB)
    cn=conn.cursor()
    conn.text_factory = unicode #sqlite.OptimizedUnicode

    try:
        # in old version something went wrong with deleteing old unused folders
        for _ in range(1,10):
            cn.execute('delete from folders where ParentFolder not in (select idFolder from folders) and ParentFolder is not null')

        cn.execute('delete from files where idFolder not in( select idFolder from folders)')


        cn.execute( "delete from TagsInFiles where idFile not in(select idFile from Files )")
        cn.execute( "delete from TagContents where idTagContent not in (select idTagContent from TagsInFiles)")
        # Only delete tags which are not translated!
        cn.execute( "delete from TagTypes where idTagType not in (select idTagType from TagContents) and TagType = TagTranslation")

    except Exception,msg:
        common.log("MPDB.cleanup_keywords", "%s - %s"%(Exception,msg), xbmc.LOGERROR )
        cn.close()
        raise

    conn.commit()
    cn.close()

def pic_exists(picpath,picfile):
    """
    Check wether or not a file exists in the DB
    """
    conn = sqlite.connect(pictureDB)
    cn=conn.cursor()

    try:
        cn.execute("""SELECT strPath, strFilename FROM "main"."files" WHERE strPath = (?) AND strFilename = (?);""",(picpath,picfile,) )
    except Exception,msg:
        common.log("MPDB.pic_exists", "EXCEPTION >> pic_exists %s,%s"%(picpath,picfile), xbmc.LOGERROR )
        common.log("MPDB.pic_exists", "%s - %s"%(Exception,msg), xbmc.LOGERROR )
        raise Exception, msg
    if len(cn.fetchmany())==0:

        retour= False
    else:
        retour= True
    cn.close()
    return retour

def listdir(path):
    """
    List files from DB where path
    """

    conn = sqlite.connect(pictureDB)
    cn=conn.cursor()
    conn.text_factory = unicode #sqlite.OptimizedUnicode

    try:
        cn.execute( u"SELECT f.strFilename FROM files f,folders p WHERE f.idFolder=p.idFolder AND p.FullPath=(?)",(path,))
    except Exception,msg:
        common.log( "listdir", "path = "%path, xbmc.LOGERROR )
        common.log( "listdir", "%s - %s"%(Exception,msg), xbmc.LOGERROR )
        cn.close()
        raise

    retour = [row[0] for row in cn]
    #print retour
    cn.close()
    return retour

tagTypeDBKeys = {}
def file_insert(path,filename,dictionnary,update=False, sha=0):
    """
    insert into file database the dictionnary values into the dictionnary keys fields
    keys are DB fields ; values are DB values
    """
    global tagTypeDBKeys

    if update :#si update alors on doit updater et non pas insert
        if pic_exists(path,filename):
            #print "file exists in database and rescan is set to true..."
            RequestWithBinds(""" DELETE FROM files WHERE idFolder = (SELECT idFolder FROM folders WHERE FullPath=?) AND strFilename=? """,(path,filename))
            cleanup_keywords()
    conn = sqlite.connect(pictureDB)
    cn=conn.cursor()


    #idFile integer primary key, idFolder integer, strPath text, strFilename text, ftype text, DateAdded DATETIME,  Thumb text,  "ImageRating" text, 

    conn.text_factory = unicode#sqlite.OptimizedUnicode
    try:
        imagedatetime = ""
        if  "EXIF DateTimeOriginal" in dictionnary:
            imagedatetime = dictionnary["EXIF DateTimeOriginal"]
            #print "1 = " + str(imagedatetime)
        if len(imagedatetime.strip()) < 10 and "ImageDateTime" in dictionnary:
            imagedatetime = dictionnary["ImageDateTime"]
            #print "2 = " + str(imagedatetime)
        if len(imagedatetime.strip()) < 10 and "EXIF DateTimeDigitized" in dictionnary:
            imagedatetime = dictionnary["EXIF DateTimeDigitized"]
            #print "3 = " + str(imagedatetime)
         
        try:
            dictionnary['YYYY-MM'] = imagedatetime[:7]
        except:
            pass
        
        cn.execute( """INSERT INTO files(idFolder, strPath, strFilename, ftype, DateAdded,  Thumb,  ImageRating, ImageDateTime, Sha) values (?, ?, ?, ?, ?, ?, ?, ?, ?)""", 
                      ( dictionnary["idFolder"],  dictionnary["strPath"], dictionnary["strFilename"], dictionnary["ftype"], dictionnary["DateAdded"], dictionnary["Thumb"], dictionnary["ImageRating"], imagedatetime, sha ) )
        conn.commit()
    except Exception,msg:

        common.log("file_insert", "path = %s"%common.smart_unicode(filename).encode('utf-8'), xbmc.LOGERROR)
        common.log("file_insert",  "%s - %s"%(Exception,msg), xbmc.LOGERROR )
        common.log( "file_insert", """INSERT INTO files('%s') values (%s)""" % ( "','".join(dictionnary.keys()) , ",".join(["?"]*len(dictionnary.values())) ), xbmc.LOGERROR )
        conn.commit()
        cn.close()
        raise MyPictureDB


    # meta table inserts
    cn.execute("SELECT idFile FROM files WHERE strPath = ? AND strFilename = ?",(path,filename,) )
    idfile = [row[0] for row in cn][0]
    tags_insert(conn, cn, idfile, filename, path, dictionnary)

    conn.commit()
    cn.close()
    return True


def tags_insert(conn, cn, idfile, filename, path, dictionnary):

    # loop over tags dictionary
    for tag_type, value in dictionnary.iteritems():

        if isinstance(value, basestring) and dictionnary[tag_type]:

            # exclude the following tags
            if tag_type not in ['sha', 'strFilename', 'strPath',
                               'mtime', 'ftype',
                               'source', 'urgency', 'time created', 'date created']:

                tag_values = dictionnary[tag_type].split(lists_separator)

                tag_type = tag_type[0].upper() + tag_type[1:]

                for value in tag_values:

                    # change dates
                    if tag_type == 'EXIF DateTimeOriginal':
                        value = value[:10]

                    # first make sure that the tag exists in table TagTypes
                    # is it already in our list?
                    if not tag_type in tagTypeDBKeys:

                        # not in list therefore insert into table TagTypes
                        try:
                            cn.execute(""" INSERT INTO TagTypes(tagType, TagTranslation) VALUES(?, ?) """,(tag_type,tag_type))
                        except Exception,msg:
                            if str(msg)=="column TagType is not unique":
                                pass
                            else:
                                common.log("tags_insert", "path = %s"%common.smart_unicode(filename).encode('utf-8'), xbmc.LOGERROR)
                                common.log("tags_insert",  'tagType = %s'%tag_type, xbmc.LOGERROR )
                                common.log("tags_insert",  "\t%s - %s"%(Exception,msg), xbmc.LOGERROR )

                        # select the key of the tag from table TagTypes
                        cn.execute("SELECT min(idTagType) FROM TagTypes WHERE TagType = ? ",(tag_type,) )
                        id_tag_type= [row[0] for row in cn][0]
                        tagTypeDBKeys[tag_type] = id_tag_type
                    else :
                        id_tag_type = tagTypeDBKeys[tag_type]

                    try:
                        cn.execute(""" INSERT INTO TagContents(idTagType,TagContent) VALUES(?,?) """,(id_tag_type,value))
                    except Exception,msg:
                        if str(msg)=="columns idTagType, TagContent are not unique":
                            pass
                        else:
                            common.log("tags_insert", "path = %s"%common.smart_unicode(filename).encode('utf-8'), xbmc.LOGERROR)
                            common.log("tags_insert", 'EXCEPTION >> tags', xbmc.LOGERROR )
                            common.log("tags_insert", 'tagType = %s'%tag_type, xbmc.LOGERROR )
                            common.log("tags_insert", 'tagValue = %s'%common.smart_utf8(value), xbmc.LOGERROR )
                            common.log("tags_insert", "%s - %s"%(Exception,msg), xbmc.LOGERROR )

                    # this block should be obsolet now!!!

                    #Then, add the corresponding id of file and id of tag inside the TagsInFiles database
                    try:
                        cn.execute(""" INSERT INTO TagsInFiles(idTagContent,idFile) SELECT t.idTagContent, %d FROM TagContents t WHERE t.idTagType=%d AND t.TagContent = ? """%(idfile,id_tag_type), (value,))


                    # At first column was named idTag then idTagContent
                    except Exception,msg:
                        if str(msg)=="table TagsInFiles has no column named idTagContent":
                            try:
                                cn.execute("DROP TABLE TagsInFiles")
                                cn.execute('CREATE TABLE "TagsInFiles" ("idTagContent" INTEGER NOT NULL, "idFile" INTEGER NOT NULL)')

                                cn.execute(""" INSERT INTO TagsInFiles(idTagContent,idFile) SELECT t.idTagContent, %d FROM TagContents t WHERE t.idTagType=%d AND t.TagContent = ? """%(idfile,id_tag_type), (value,))
                            except:
                                common.log("tags_insert", "Error while ALTER TABLE TagsInFiles ", xbmc.LOGERROR)
                                common.log("tags_insert", "%s - %s"% (Exception,msg), xbmc.LOGERROR )
                        else:
                            common.log("tags_insert", "Error while adding TagsInFiles")
                            common.log("tags_insert", "%s - %s"% (Exception,msg) )
                            common.log("tags_insert", "%s %s - %s"%(idfile,id_tag_type,common.smart_utf8(value)))
                            #print """ INSERT INTO TagsInFiles(idTagContent,idFile) SELECT t.idTagContent, %d FROM TagContents t WHERE t.idTagType=%d AND t.TagContent = '%s' """%(idFile,id_tag_type,value)


    return True


def folder_insert(foldername,folderpath,parentfolderID,haspic):
    """insert into folders database, the folder name, folder parent, full path and if has pics
        Return the id of the folder inserted"""
    conn = sqlite.connect(pictureDB)
    cn=conn.cursor()
    conn.text_factory = sqlite.OptimizedUnicode

    #insert in the folders database
    try:
        cn.execute("""INSERT INTO folders(FolderName,ParentFolder,FullPath,HasPics) VALUES (?,?,?,?) """,(foldername,parentfolderID,folderpath,haspic))
    except sqlite.IntegrityError:
        pass
    conn.commit()
    #return the id of the folder inserted
    cn.execute("""SELECT idFolder FROM folders where FullPath= ?""",(folderpath,))
    try:
        retour = [row for (row,) in cn][0]
    except:
        retour = 0
    cn.close()
    return retour

def get_children(folderid):
    #print "get_children(" + str(folderid) + ")"
    """search all children folders ids for the given folder id"""
    childrens=[c[0] for c in RequestWithBinds("SELECT idFolder FROM folders WHERE ParentFolder=? ", (folderid,))]
    list_child=[]
    list_child.extend(childrens)
    for idchild in childrens:
        list_child.extend(get_children(idchild))
    return list_child

def del_pic(picpath,picfile=None): #TODO : revoir la vérif du dossier inutile
    """Supprime le chemin/fichier de la base. Si aucun fichier n'est fourni, toutes les images du chemin sont supprimées de la base"""

    if picfile:
        #on supprime le fichier de la base
        #print """DELETE FROM files WHERE idFolder = (SELECT idFolder FROM folders WHERE FullPath="%s") AND strFilename="%s" """%(picpath,picfile)
        RequestWithBinds("""DELETE FROM files WHERE idFolder = (SELECT idFolder FROM folders WHERE FullPath=?) AND strFilename=? """,(picpath,picfile))

    else:

        try:
            if picpath:
                idpath = RequestWithBinds("""SELECT idFolder FROM folders WHERE FullPath = ? """, (picpath,))[0][0]#le premier du tuple à un élément
            else:
                idpath = Request("""SELECT idFolder FROM folders WHERE FullPath is null""")[0][0]#le premier du tuple à un élément

            common.log( "del_pic", "(%s,%s)"%( common.smart_utf8(picpath),common.smart_utf8(picfile)) )

            deletelist=[]#va lister les id des dossiers à supprimer
            deletelist.append(idpath)#le dossier en paramètres est aussi à supprimer
            deletelist.extend(get_children(str(idpath)))#on ajoute tous les enfants en sous enfants du dossier

            Request( """DELETE FROM files WHERE idFolder in ("%s")"""%""" "," """.join([str(i) for i in deletelist]) )
            common.log( "del_pic", """DELETE FROM folders WHERE idFolder in ("%s") """%""" "," """.join([str(i) for i in deletelist]))
            Request( """DELETE FROM folders WHERE idFolder in ("%s") """%""" "," """.join([str(i) for i in deletelist]) )
        except:
            pass

    return

def sha_of_file ( filepath ) :
    #found here : http://sebsauvage.net/python/doublesdetector.py
    #thanks sebsauvage for all its snippets !
    """ Compute SHA (Secure Hash Algorythm) of a file.
        Input : filepath : full path and name of file (eg. 'c:\windows\emm386.exe')
        Output : string : contains the hexadecimal representation of the SHA of the file.
                          returns '0' if file could not be read (file not found, no read rights...)
    """

    try:
        import hashlib
        digest = hashlib.md5()
    except ImportError:
        # for Python << 2.5
        import md5
        digest = md5.new()    

    filepath = common.smart_unicode(filepath)
    try:
        try:
            filehandle = open(filepath,'rb')
        except:
            filehandle = open(filepath.encode('utf-8'),'rb')

        data = filehandle.read(65536)
        while len(data) != 0:
            digest.update(data)
            data = filehandle.read(65536)
        filehandle.close()
    except:
        print_exc()
        return '0'
    else:
        return digest.hexdigest()

def stored_sha (path,filename): 
    #return the SHA in DB for the given picture
    try:
        return [row for row in RequestWithBinds( """select sha from files where strPath=? and strFilename=? """,(path,filename))][0][0]
    except:
        return "0"
"""
def getFileMtime(path,filename):   
    #return the modification time 'mtime' in DB for the given picture
    return [row for row in RequestWithBinds( "select mtime from files where strPath=? and strFilename=? "%(path,filename))][0][0]

def DB_deltree(picpath):
    pass
"""

def get_rating(path,filename):   
    try:
        return [row for row in RequestWithBinds( """SELECT files.ImageRating FROM files WHERE strPath=? AND strFilename=? """, (path,filename) )][0][0]
    except IndexError:
        return None



###################################
# Filter Wizard functions
#####################################

def filterwizard_result(set_tags, unset_tags, match_all, start_date='', end_date=''):
    if len(set_tags) == 0 and len(unset_tags) == 0 and start_date == '' and end_date == '':
        return
    
    set_tags_array = set_tags.split("|||")

    unset_tags_array = unset_tags.split("|||")    

    outer_select = "SELECT distinct strPath,strFilename, ImageDateTime FROM FILES WHERE 1=1 "

    # These selects are joined with IN clause
    inner_select = "SELECT tif.idfile FROM TagContents tc, TagsInFiles tif , TagTypes tt WHERE tif.idTagContent = tc.idTagContent AND tc.idTagType = tt.idTagType "

    # Build the conditions
    if match_all == "1":
        if len(set_tags) > 0:
            for filter_tags in set_tags_array:

                key_value = filter_tags.split("||")
                key = key_value[0]
                value = key_value[1].replace("'", "''")

                condition = "AND tt.TagTranslation = '"+key+"' AND tc.TagContent = '"+value+"' "
                outer_select += " AND idFile in ( " + inner_select + condition + " ) "

        if len(unset_tags) > 0:
            for filter_tags in unset_tags_array:

                key_value = filter_tags.split("||")
                key = key_value[0]
                value = key_value[1].replace("'", "''")

                condition = "AND tt.TagTranslation = '"+key+"' AND tc.TagContent = '"+value+"' "
                outer_select += " AND idFile not in ( " + inner_select + condition + " ) "            

    else:
        old_key = ""
        old_value = ""

        if len(set_tags) > 0:        
            for filter_tags in set_tags_array:

                key_value = filter_tags.split("||")
                key = key_value[0]
                value = key_value[1].replace("'", "''")

                if key != old_key:
                    if len(old_key) > 0:
                        condition = "AND tt.TagTranslation = '"+old_key+"' AND tc.TagContent in( "+old_value+" ) "
                        outer_select += " AND idFile in ( " + inner_select + condition + " ) "
                    old_key = key
                    old_value = "'" + value + "'"
                else:
                    old_value += ", '" + value + "'"
            condition = "AND tt.TagTranslation = '"+old_key+"' AND tc.TagContent in( "+old_value+" ) "
            outer_select += " AND idFile in ( " + inner_select + condition + " ) "

        if len(unset_tags) > 0:
            for filter_tags in unset_tags_array:

                key_value = filter_tags.split("||")
                key = key_value[0]
                value = key_value[1].replace("'", "''")

                if key != old_key:
                    if len(old_key) > 0:
                        condition = "AND tt.TagTranslation = '"+old_key+"' AND tc.TagContent in( "+old_value+" ) "
                        outer_select += " AND idFile not in ( " + inner_select + condition + " ) "
                    old_key = key
                    old_value = "'" + value + "'"
                else:
                    old_value += ", '" + value + "'"

            condition = "AND tt.TagTranslation = '"+old_key+"' AND tc.TagContent in( "+old_value+" ) "
            outer_select += " AND idFile not in ( " + inner_select + condition + " ) "

    outer_select += " order by imagedatetime "
    
    # test if start or end_date is set
    if start_date != '' or end_date != '':
        dates_set = 0
        outer_select = 'Select strPath,strFilename from (' + outer_select + ' ) '
        
        if start_date != '':
            dates_set += 1
            outer_select += " where ImageDateTime >= date('%s') "%(start_date,)
        
        if end_date != '':
            dates_set += 1
            if dates_set == 1:
                outer_select += " where ImageDateTime <= date('%s') "%(end_date,)
            else:
                outer_select += " and ImageDateTime <= date('%s') "%(end_date,)
                
    else:
        outer_select = 'Select strPath,strFilename from (' + outer_select + ' ) '
            
    common.log('filterwizard_result', outer_select, xbmc.LOGDEBUG)
    return [row for row in Request(outer_select)]


def filterwizard_list_filters():
    filterarray = []
    for row in Request( """select strFilterName from FilterWizard order by 1"""):
        filterarray.append(row[0])
    return filterarray


def filterwizard_delete_filter(filter_name):
    RequestWithBinds( "delete from FilterWizard where strFilterName = ? ",(filter_name, ))


def filterwizard_save_filter(filter_name, items, bmatch_all, start_date ='', end_date = ''):

    match_all = (1 if bmatch_all == True else 0)
    if [row for row in RequestWithBinds( "select count(*) from FilterWizard where strFilterName = ? ",(filter_name, ))] [0][0] == 0:
        RequestWithBinds( "insert into FilterWizard(strFilterName, bMatchAll, StartDate, EndDate) values (?, ?, ?, ?) ",(filter_name, match_all, start_date, end_date ))
    else:
        RequestWithBinds( "update FilterWizard set bMatchAll = ?, StartDate = ?, EndDate = ? where strFiltername = ? ",(match_all, start_date, end_date, filter_name ))
    
    filter_key = [row for row in RequestWithBinds( "select pkFilter from FilterWizard where strFilterName = ? ",(filter_name, ))] [0][0]
    #common.log("MPDB.filterwizard_save_filter", "filter_key = %d"%filter_key, xbmc.LOGNOTICE )
    RequestWithBinds("delete from FilterWizardItems where fkfilter = ?", (filter_key, ))
    for item, state in items.iteritems():
        if state != 0:
            RequestWithBinds("insert into FilterWizardItems(fkFilter, strItem, nState) values(?, ?, ?)", (filter_key, item, state))
       
        
def filterwizard_load_filter(filter_name):
    items = {}
    match_all = 0
    start_date = ''
    end_date = ''
    #
    if [row for row in RequestWithBinds( "select count(*) from FilterWizard where strFilterName = ? ",(filter_name, ))] [0][0] > 0:
        filter_key, match_all, start_date, end_date = [row for row in RequestWithBinds( "select pkFilter, bMatchAll, StartDate, EndDate from FilterWizard where strFilterName = ? ",(filter_name, ))] [0]
        for state, item in RequestWithBinds( "select nState, strItem from FilterWizardItems where fkFilter = ?", (filter_key,)):
            items[item] = state

    return items, (True if match_all == 1 else False), start_date, end_date
    

###################################
# Collection functions
#####################################
def collections_list():
    """List all available collections"""
    return [row for row in Request( """SELECT CollectionName FROM Collections""")]


def collection_new(Colname):
    """Add a new collection"""       
    if Colname :
        RequestWithBinds( "INSERT INTO Collections(CollectionName) VALUES (?) ",(Colname, ))
    else:
        common.log( "collection_new", "User did not specify a name for the collection.")
        
        
def collection_delete(Colname):      
    """delete a collection"""
    common.log( "collection_delete", "Name = %s"%Colname)
    if Colname:
        RequestWithBinds( """DELETE FROM FilesInCollections WHERE idCol=(SELECT idCol FROM Collections WHERE CollectionName=?)""", (Colname,))
        RequestWithBinds( """DELETE FROM Collections WHERE CollectionName=? """,(Colname,) )
    else:
        common.log( "collection_delete",  "User did not specify a name for the collection" )


def collection_get_pics(Colname):      
    """List all pics associated to the Collection given as Colname"""
    return [row for row in RequestWithBinds( """SELECT strPath,strFilename FROM Files WHERE idFile IN (SELECT idFile FROM FilesInCollections WHERE idCol IN (SELECT idCol FROM Collections WHERE CollectionName=?)) ORDER BY ImageDateTime ASC""",(Colname,))]


def collection_rename(Colname,newname):   
    """rename give collection"""
    if Colname:
        RequestWithBinds( """UPDATE Collections SET CollectionName = ? WHERE CollectionName=? """, (newname,Colname) )
    else:
        common.log( "collection_rename",  "User did not specify a name for the collection")


def collection_add_pic(Colname,filepath,filename):    

    #cette requête ne vérifie pas si :
    #   1- le nom de la collection existe dans la table Collections
    #   2- si l'image est bien une image en base de donnée Files
    #ces points sont solutionnés partiellement car les champs ne peuvent être NULL
    #   3- l'association idCol et idFile peut apparaitre plusieurs fois...
    #print """(SELECT idFile FROM files WHERE strPath="%s" AND strFilename="%s")"""%(filepath,filename)
    RequestWithBinds( """INSERT INTO FilesInCollections(idCol,idFile) VALUES ( (SELECT idCol FROM Collections WHERE CollectionName=?) , (SELECT idFile FROM files WHERE strPath=? AND strFilename=?) )""",(Colname,filepath,filename) )


def collection_del_pic(Colname,filepath,filename):
    common.log("collection_del_pic","%s, %s, %s"%(Colname,filepath,filename))
    RequestWithBinds( """DELETE FROM FilesInCollections WHERE idCol=(SELECT idCol FROM Collections WHERE CollectionName=?) AND idFile=(SELECT idFile FROM files WHERE strPath=? AND strFilename=?)""",(Colname,filepath,filename) )


####################
# Periodes functions
#####################
def periods_list():
    """List all periodes"""
    return [row for row in Request( """SELECT PeriodeName,DateStart,DateEnd FROM Periodes""")]

def period_add(periodname,datestart,dateend):
    #datestart et dateend doivent être au format string ex.: "datetime('2009-07-12')" ou "strftime('%Y',now)"
    RequestWithBinds( """INSERT INTO Periodes(PeriodeName,DateStart,DateEnd) VALUES (?,%s,%s)"""%(datestart,dateend), (periodname,) )
    return

def period_delete(periodname):
    RequestWithBinds( """DELETE FROM Periodes WHERE PeriodeName=? """,(periodname,) )
    return

def period_rename(periodname,newname,newdatestart,newdateend):

    RequestWithBinds( """UPDATE Periodes SET PeriodeName = ?,DateStart = datetime(?) , DateEnd = datetime(?) WHERE PeriodeName=? """,(newname,newdatestart,newdateend,periodname) )
    return

"""Get pics for the given period name"""
"""
def get_pics_in_period(periodname):    
    
    period = RequestWithBinds( "SELECT DateStart,DateEnd FROM Periodes WHERE PeriodeName=?", (periodname,) )
    return [row for row in RequestWithBinds( "SELECT strPath,strFilename FROM files WHERE datetime(ImageDateTime) BETWEEN ? AND ? ORDER BY ImageDateTime ASC",period )]
"""

def search_in_files(tag_type, tagvalue, count=False):
    val = tagvalue.lower().replace("'", "''")

    if count:
        return [row for row in RequestWithBinds( """select count(distinct fi.strFilename||fi.strPath)
                                                      from TagTypes tt, TagContents tc, TagsInFiles tif, Files fi
                                                     where tt.idTagType = tc.idTagType
                                                       and tc.idTagContent = tif.idTagContent
                                                       and tt.TagTranslation = ?
                                                       and lower(tc.TagContent) LIKE '%%%s%%'
                                                       and tif.idFile = fi.idFile"""%val, (tag_type,))][0][0]
    else:
        return [row for row in RequestWithBinds( """select distinct fi.strPath, fi.strFilename
                                                      from TagTypes tt, TagContents tc, TagsInFiles tif, Files fi
                                                     where tt.idTagType = tc.idTagType
                                                       and tc.idTagContent = tif.idTagContent
                                                       and tt.TagTranslation = ?
                                                       and lower(tc.TagContent) LIKE '%%%s%%'
                                                       and tif.idFile = fi.idFile"""%val, (tag_type, ))]


def get_gps(filepath,filename):

    latR = RequestWithBinds( """select tc.TagContent from TagTypes tt, TagContents tc, TagsInFiles tif, Files fi
                                where tt.TagType = 'GPS GPSLatitudeRef'
                                  and tt.idTagType = tc.idTagType
                                  and tc.idTagContent = tif.idTagContent
                                  and tif.idFile = fi.idFile
                                  and fi.strPath = ?
                                  and fi.strFilename = ?""",  (filepath,filename) )
    lat = RequestWithBinds( """select tc.TagContent from TagTypes tt, TagContents tc, TagsInFiles tif, Files fi
                                where tt.TagType = 'GPS GPSLatitude'
                                  and tt.idTagType = tc.idTagType
                                  and tc.idTagContent = tif.idTagContent
                                  and tif.idFile = fi.idFile
                                  and fi.strPath = ?
                                  and fi.strFilename = ?""",  (filepath,filename) )
    lonR = RequestWithBinds( """select tc.TagContent from TagTypes tt, TagContents tc, TagsInFiles tif, Files fi
                                where tt.TagType = 'GPS GPSLongitudeRef'
                                  and tt.idTagType = tc.idTagType
                                  and tc.idTagContent = tif.idTagContent
                                  and tif.idFile = fi.idFile
                                  and fi.strPath = ?
                                  and fi.strFilename = ?""",  (filepath,filename) )
    lon = RequestWithBinds( """select tc.TagContent from TagTypes tt, TagContents tc, TagsInFiles tif, Files fi
                                where tt.TagType = 'GPS GPSLongitude'
                                  and tt.idTagType = tc.idTagType
                                  and tc.idTagContent = tif.idTagContent
                                  and tif.idFile = fi.idFile
                                  and fi.strPath = ?
                                  and fi.strFilename = ?""",  (filepath,filename) )
    try:
        latR=latR[0][0]
        lat=lat[0][0]
        lonR=lonR[0][0]
        lon=lon[0][0]
    except IndexError:
        return None
    if not latR or not lat or not lonR or not lon: 
        return None                            

    #tuplat = lat.replace(" ","").replace("[","").replace("]","").split(",")
    #tuplon = lon.replace(" ","").replace("[","").replace("]","").split(",")
    lD,lM,lS = lat.replace(" ","").replace("[","").replace("]","").split(",")[:3]
    LD,LM,LS = lon.replace(" ","").replace("[","").replace("]","").split(",")[:3]
    exec("lD=%s"%lD)
    exec("lM=%s"%lM)
    exec("lS=%s"%lS)
    exec("LD=%s"%LD)
    exec("LM=%s"%LM)
    exec("LS=%s"%LS)
    latitude =  (int(lD)+(int(lM)/60.0)+(int(lS)/3600.0)) * (latR=="S" and -1 or 1)
    longitude = (int(LD)+(int(LM)/60.0)+(int(LS)/3600.0)) * (lonR=="W" and -1 or 1)
    return (latitude,longitude)

######################################"
#  Fonctions pour les dossiers racines
######################################"

def get_all_root_folders():
    "return folders which are root for scanning pictures"
    return [row for row in Request( """SELECT path,recursive,remove,exclude FROM Rootpaths ORDER BY path""")]

def add_root_folder(path,recursive,remove,exclude):
    "add the path root inside the database. Recursive is 0/1 for recursive scan, remove is 0/1 for removing files that are not physically in the place"
    cleanup_keywords()
    RequestWithBinds( """INSERT INTO Rootpaths(path,recursive,remove,exclude) VALUES (?,?,?,?)""",(common.smart_unicode(path),recursive,remove,exclude) )
    common.log( "add_root_folder", "%s"%common.smart_utf8(path))

def get_root_folders(path):
    common.log( "get_root_folders", "%s"%common.smart_utf8(path))
    #print common.smart_utf8(path)
    return [row for row in RequestWithBinds( """SELECT path,recursive,remove,exclude FROM Rootpaths WHERE path=? """, (common.smart_unicode(path),) )][0]


def delete_root(path):
    "remove the given rootpath, remove pics from this path, ..."
    common.log( "delete_root", "name = %s"%common.smart_utf8(path))
    #first remove the path with all its pictures / subfolders / keywords / pictures in collections...
    delete_paths_from_root(path)
    #then remove the rootpath itself
    common.log( "delete_root",   """DELETE FROM Rootpaths WHERE path='%s' """%common.smart_utf8(path))
    RequestWithBinds( """DELETE FROM Rootpaths WHERE path=? """, (common.smart_unicode(path),) )


def delete_paths_from_root(path):
    "remove the given rootpath, remove pics from this path, ..."
    common.log( "delete_paths_from_root", "name = %s"%common.smart_utf8(path))
    #cptremoved = 0
    try:
        idpath = RequestWithBinds( """SELECT idFolder FROM folders WHERE FullPath = ?""",(common.smart_unicode(path),) )[0][0]
    except:
        common.log( "delete_paths_from_root",  "Path %s not found"%path)
        return 0

    cptremoved = Request( """SELECT count(*) FROM files WHERE idFolder='%s'"""%idpath )[0][0]
    common.log( "delete_paths_from_root",  """DELETE FROM files WHERE idFolder='%s'"""%idpath)
    Request( """DELETE FROM files WHERE idFolder='%s'"""%idpath)

    for idchild in all_children_of_folder(idpath):

        Request( """DELETE FROM FilesInCollections WHERE idFile in (SELECT idFile FROM files WHERE idFolder='%s')"""%idchild )
        cptremoved = cptremoved + Request( """SELECT count(*) FROM files WHERE idFolder='%s'"""%idchild)[0][0]
        Request( """DELETE FROM files WHERE idFolder='%s'"""%idchild)
        Request( """DELETE FROM folders WHERE idFolder='%s'"""%idchild)
    common.log( "delete_paths_from_root",  """DELETE FROM folders WHERE idFolder='%s'"""%idpath)
    Request( """DELETE FROM folders WHERE idFolder='%s'"""%idpath)

    for periodname,datestart,dateend in periods_list():
        if Request( """SELECT count(*) FROM files WHERE datetime(ImageDateTime) BETWEEN '%s' AND '%s'"""%(datestart,dateend) )[0][0]==0:
            Request( """DELETE FROM Periodes WHERE PeriodeName='%s'"""%periodname )
    cleanup_keywords()
    return cptremoved

"""
def MakeRequest(field,comparator,value):
    return Request( "SELECT p.FullPath,f.strFilename FROM files f,folders p WHERE f.idFolder=p.idFolder AND %s %s %s "%(field,comparator,value))
"""

def Request(SQLrequest):
    binds = []
    return RequestWithBinds(SQLrequest, binds)

def RequestWithBinds(SQLrequest, bindVariablesOrg):
    conn = sqlite.connect(pictureDB)
    conn.text_factory = unicode #sqlite.OptimizedUnicode
    cn=conn.cursor()
    bindVariables = []
    for value in bindVariablesOrg:
        if type(value) == type('str'):
            bindVariables.append(common.smart_unicode(value))
        else:
            bindVariables.append(value)
    try:
        cn.execute( SQLrequest, bindVariables )
        conn.commit()
        retour = [row for row in cn]
    except Exception,msg:
        if msg.args[0].startswith("no such column: files.GPS GPSLatitudeRef"):
            pass
        else:
            try:
                common.log( "RequestWithBinds", "The request failed :", xbmc.LOGERROR )
                common.log( "RequestWithBinds", "%s - %s"%(Exception,msg), xbmc.LOGERROR )
                common.log( "RequestWithBinds",  "SQL RequestWithBinds > %s"%SQLrequest, xbmc.LOGERROR)
                i = 1
                for var in bindVariables:
                    common.log( "RequestWithBinds", "SQL RequestWithBinds %d> %s"%(i,var), xbmc.LOGERROR)
                    i=i+1
            except:
                pass
        retour= []
    cn.close()
    return retour


def search_tag(tag=None,tag_type='a',limit=-1,offset=-1):
    """Look for given keyword and return the list of pictures.
If tag is not given, pictures with no keywords are returned"""
    if tag is not None: #si le mot clé est fourni
        return [row for row in RequestWithBinds( """SELECT distinct strPath,strFilename FROM files f, TagContents tc, TagsInFiles tif, TagTypes tt WHERE f.idFile = tif.idFile AND tif.idTagContent = tc.idTagContent AND tc.TagContent = ? and tc.idTagType = tt.idTagType  and length(trim(tt.TagTranslation))>0 and tt.TagTranslation = ?  order by imagedatetime LIMIT %s OFFSET %s """%(limit,offset), (tag.encode("utf8"),tag_type.encode("utf8")) )]
    else: #sinon, on retourne toutes les images qui ne sont pas associées à des mots clés
        return [row for row in Request( """SELECT distinct strPath,strFilename FROM files WHERE idFile NOT IN (SELECT DISTINCT idFile FROM TagsInFiles) order by imagedatetime LIMIT %s OFFSET %s"""%(limit,offset) )]


def default_tagtypes_translation():

    """Return a list of all keywords in database """
    
    RequestWithBinds("update TagTypes set TagTranslation = ? where TagTranslation =  'Country/primary location name'", (common.getstring(30700),))
    RequestWithBinds("update TagTypes set TagTranslation = ? where TagTranslation =  'Photoshop:Country'", (common.getstring(30700),))
    RequestWithBinds("update TagTypes set TagTranslation = ? where TagTranslation =  'Iptc4xmpExt:CountryName'", (common.getstring(30700),))

    RequestWithBinds("update TagTypes set TagTranslation = ? where TagTranslation =  'Country/primary location code'", (common.getstring(30701),))
    RequestWithBinds("update TagTypes set TagTranslation = ? where TagTranslation =  'Iptc4xmpCore:CountryCode'", (common.getstring(30701),))
    RequestWithBinds("update TagTypes set TagTranslation = ? where TagTranslation =  'Iptc4xmpCore:Country'", (common.getstring(30701),))

    RequestWithBinds("update TagTypes set TagTranslation = ? where TagTranslation =  'Province/state'", (common.getstring(30702),))
    RequestWithBinds("update TagTypes set TagTranslation = ? where TagTranslation =  'Photoshop:State'", (common.getstring(30702),))
    RequestWithBinds("update TagTypes set TagTranslation = ? where TagTranslation =  'Iptc4xmpExt:ProvinceState'", (common.getstring(30702),))

    RequestWithBinds("update TagTypes set TagTranslation = ? where TagTranslation = 'Photoshop:City'", (common.getstring(30703),))
    RequestWithBinds("update TagTypes set TagTranslation = ? where TagTranslation = 'Iptc4xmpExt:City'", (common.getstring(30703),))
    RequestWithBinds("update TagTypes set TagTranslation = ? where TagTranslation = 'City'", (common.getstring(30703),))

    RequestWithBinds("update TagTypes set TagTranslation = ? where TagTranslation =  'Iptc4xmpCore:Location'", (common.getstring(30704),))

    RequestWithBinds("update TagTypes set TagTranslation = ? where TagTranslation = 'Iptc4xmpExt:Event'", (common.getstring(30705),))

    RequestWithBinds("update TagTypes set TagTranslation = ? where TagTranslation =  'DateAdded'", (common.getstring(30706),))
    
    RequestWithBinds("update TagTypes set TagTranslation = ? where TagTranslation =  'EXIF DateTimeOriginal'", (common.getstring(30707),))
    
    RequestWithBinds("update TagTypes set TagTranslation = ? where TagTranslation =  'Photoshop:DateCreated'", (common.getstring(30708),))
    RequestWithBinds("update TagTypes set TagTranslation = ? where TagTranslation =  'Image DateTime'", (common.getstring(30708),))

    RequestWithBinds("update TagTypes set TagTranslation = ? where TagTranslation = 'Caption/abstract'", (common.getstring(30709),))
    RequestWithBinds("update TagTypes set TagTranslation = ? where TagTranslation = 'Dc:description'", (common.getstring(30709),))
    RequestWithBinds("update TagTypes set TagTranslation = ? where TagTranslation = 'Iptc4xmpCore:Description'", (common.getstring(30709),))

    RequestWithBinds("update TagTypes set TagTranslation = ? where TagTranslation = 'Iptc4xmpCore:Headline'", (common.getstring(30710),))
    RequestWithBinds("update TagTypes set TagTranslation = ? where TagTranslation =  'Photoshop:Headline'", (common.getstring(30710),))
    RequestWithBinds("update TagTypes set TagTranslation = ? where TagTranslation =  'Headline'", (common.getstring(30710),))

    RequestWithBinds("update TagTypes set TagTranslation = ? where TagTranslation = 'Object name'", (common.getstring(30711),))
    RequestWithBinds("update TagTypes set TagTranslation = ? where TagTranslation = 'Dc:title'", (common.getstring(30711),))
    RequestWithBinds("update TagTypes set TagTranslation = ? where TagTranslation = 'Iptc4xmpCore:Title'", (common.getstring(30711),))

    RequestWithBinds("update TagTypes set TagTranslation = ? where TagTranslation = 'Writer/editor'", (common.getstring(30712),))
    RequestWithBinds("update TagTypes set TagTranslation = ? where TagTranslation = 'By-line'", (common.getstring(30712),))
    RequestWithBinds("update TagTypes set TagTranslation = ? where TagTranslation = 'Dc:creator'", (common.getstring(30712),))
    
    RequestWithBinds("update TagTypes set TagTranslation = ? where TagTranslation = 'By-line title'", (common.getstring(30713),))

    RequestWithBinds("update TagTypes set TagTranslation = ? where TagTranslation = 'Dc:rights'", (common.getstring(30714),))
    RequestWithBinds("update TagTypes set TagTranslation = ? where TagTranslation = 'Copyright notice'", (common.getstring(30714),))

    RequestWithBinds("update TagTypes set TagTranslation = ? where TagTranslation =  'Xmp:Label'", (common.getstring(30715),))
    
    RequestWithBinds("update TagTypes set TagTranslation = ? where TagTranslation =  'Xmp:Rating'", (common.getstring(30716),))

    RequestWithBinds("update TagTypes set TagTranslation = ? where TagTranslation =  'MicrosoftPhoto:LastKeywordIPTC'", (common.getstring(30717),))
    RequestWithBinds("update TagTypes set TagTranslation = ? where TagTranslation =  'MicrosoftPhoto:LastKeywordXMP'", (common.getstring(30717),))
    RequestWithBinds("update TagTypes set TagTranslation = ? where TagTranslation =  'Dc:subject'", (common.getstring(30717),))
    RequestWithBinds("update TagTypes set TagTranslation = ? where TagTranslation =  'Iptc4xmpCore:Keywords'", (common.getstring(30717),))
    RequestWithBinds("update TagTypes set TagTranslation = ? where TagTranslation =  'Keywords'", (common.getstring(30717),))

    RequestWithBinds("update TagTypes set TagTranslation = ? where TagTranslation =  'Category'", (common.getstring(30718),))
    RequestWithBinds("update TagTypes set TagTranslation = ? where TagTranslation =  'Photoshop:Category'", (common.getstring(30718),))
    
    RequestWithBinds("update TagTypes set TagTranslation = ? where TagTranslation =  'Photoshop:SupplementalCategories'", (common.getstring(30719),))
    RequestWithBinds("update TagTypes set TagTranslation = ? where TagTranslation =  'Supplemental category'", (common.getstring(30719),))

    RequestWithBinds("update TagTypes set TagTranslation = ? where TagTranslation =  'MPReg:PersonDisplayName'", (common.getstring(30720),))
    RequestWithBinds("update TagTypes set TagTranslation = ? where TagTranslation =  'Iptc4xmpExt:PersonInImage'", (common.getstring(30720),))
    RequestWithBinds("update TagTypes set TagTranslation = ? where TagTranslation =  'Mwg-rs:RegionList:Face'", (common.getstring(30720),))

    RequestWithBinds("update TagTypes set TagTranslation = ? where TagTranslation =  'EXIF ExifImageWidth'", (common.getstring(30721),))
    
    RequestWithBinds("update TagTypes set TagTranslation = ? where TagTranslation =  'EXIF ExifImageLength'", (common.getstring(30722),))
    
    RequestWithBinds("update TagTypes set TagTranslation = ? where TagTranslation =  'EXIF SceneCaptureType'", (common.getstring(30723),))
    
    RequestWithBinds("update TagTypes set TagTranslation = ? where TagTranslation =  'EXIF Flash'", (common.getstring(30724),))

    RequestWithBinds("update TagTypes set TagTranslation = ? where TagTranslation =  'Image Model'", (common.getstring(30725),))
    
    RequestWithBinds("update TagTypes set TagTranslation = ? where TagTranslation =  'Image Make'", (common.getstring(30726),))
    
    RequestWithBinds("update TagTypes set TagTranslation = ? where TagTranslation =  'Image Artist'", (common.getstring(30727),))

    # default to not visible
    Request("update TagTypes set TagTranslation = '' where TagTranslation =  'EXIF DateTimeDigitized'")
    Request("update TagTypes set TagTranslation = '' where TagTranslation =  'EXIF DigitalZoomRatio'")
    Request("update TagTypes set TagTranslation = '' where TagTranslation =  'EXIF ExifVersion'")
    Request("update TagTypes set TagTranslation = '' where TagTranslation =  'EXIF FileSource'")
    Request("update TagTypes set TagTranslation = '' where TagTranslation =  'Image Orientation'")
    Request("update TagTypes set TagTranslation = '' where TagTranslation =  'Image ResolutionUnit'")
    Request("update TagTypes set TagTranslation = '' where TagTranslation =  'Image XResolution'")
    Request("update TagTypes set TagTranslation = '' where TagTranslation =  'Image YResolution'")
    Request("update TagTypes set TagTranslation = '' where TagTranslation =  'GPS GPSLatitude'")
    Request("update TagTypes set TagTranslation = '' where TagTranslation =  'GPS GPSLatitudeRef'")
    Request("update TagTypes set TagTranslation = '' where TagTranslation =  'GPS GPSLongitude'")
    Request("update TagTypes set TagTranslation = '' where TagTranslation =  'GPS GPSLongitudeRef'")
    Request("update TagTypes set TagTranslation = '' where TagTranslation =  'Original transmission reference'")
    Request("update TagTypes set TagTranslation = '' where TagTranslation =  'Photoshop:CaptionWriter'")
    Request("update TagTypes set TagTranslation = '' where TagTranslation =  'Photoshop:Instructions'")
    Request("update TagTypes set TagTranslation = '' where TagTranslation =  'Special instructions'")    
    Request("update TagTypes set TagTranslation = '' where TagTranslation =  'Credit'")    
    Request("update TagTypes set TagTranslation = '' where TagTranslation =  'Sub-location'")

def list_TagTypes():

    return [row for (row,) in Request( """SELECT distinct tt.TagTranslation FROM TagTypes tt, TagContents tc, TagsInFiles tif 
where length(trim(TagTranslation))>0 
and tt.idTagType = tc.idTagType
and tc.idTagContent = tif.idTagContent
ORDER BY TagTranslation ASC""" )]

def list_tagtypes_count():

    return [row for row in Request( """
SELECT tt.TagTranslation, count(distinct tagcontent)
  FROM TagTypes tt, TagContents tc, TagsInFiles tf, Files fi
 where length(trim(TagTranslation)) > 0 
   and tf.idTagContent = tc.idTagContent
   and tf.idFile = fi.idFile
   and tt.idTagType                 = tc.idTagType
group by tt.tagtranslation """   )]

def count_tagtypes(tagType,limit=-1,offset=-1):
    if tagType is not None:
        return RequestWithBinds("""SELECT count(distinct TagContent) FROM tagsInFiles tif, TagContents tc, TagTypes tt WHERE tif.idTagContent = tc.idTagContent AND tc.idTagType = tt.idTagType and length(trim(tt.TagTranslation))>0 and tt.idTagType =? """, (tagType,) )[0][0]
    else:
        return Request("""SELECT count(*) FROM TagTypes where length(trim(TagTranslation))>0""" )[0][0]

def set_tagtype_translation(TagType, TagTranslation):
    RequestWithBinds("Update TagTypes set TagTranslation = ? where TagType = ? ",(TagTranslation.encode('utf-8'), TagType.encode('utf-8')))

def get_tagtypes_translation():
    return [row for row in Request('select TagType, TagTranslation from TagTypes order by 2,1')]

def list_tags(tagType):
    """Return a list of all tags in database"""
    return [row for (row,) in Request( """select distinct TagContent from TagContents tc, TagsInFiles tif, TagTypes tt  where tc.idTagContent = tif.idTagContent and tc.idTagType = tt.idTagType and tt.TagTranslation='%s' ORDER BY LOWER(TagContent) ASC"""%tagType.encode("utf8") )]

def list_tags_count(tagType):
    """Return a list of all tags in database"""
    return [row for row in RequestWithBinds( """
    select TagContent, count(distinct idFile) 
  from TagContents tc, TagsInFiles tif, TagTypes tt  
 where tc.idTagContent = tif.idTagContent
   and tc.idTagType = tt.idTagType 
   and tt.TagTranslation=? 
group BY TagContent""",(tagType.encode("utf8"),) )]

def count_tags(kw,tagType, limit=-1,offset=-1):
    if kw is not None:
        return RequestWithBinds("""select count(distinct idFile) from  TagContents tc, TagsInFiles tif, TagTypes tt  where tc.idTagContent = tif.idTagContent and tc.TagContent = ? and tc.idTagType = tt.idTagType and tt.TagTranslation = ? """,(kw, tagType))[0][0]
    else:
        return Request("""SELECT count(*) FROM files WHERE idFile not in (SELECT DISTINCT idFile FROM TagsInFiles)""" )[0][0]


def count_pics_in_folder(folderid):
    # new part
    folderPath = RequestWithBinds("""Select FullPath from Folders where idFolder = ?""", (folderid,))[0][0]
    # mask the apostrophe
    folderPath = folderPath.replace("'", "''")
    count = Request("""select count(*) from files f, folders p where f.idFolder=p.idFolder and p.FullPath like '%s%%' """%folderPath)[0][0]
    return count

    # old part

    children = all_children_of_folder(folderid)

    cpt = Request("SELECT count(*) FROM files f,folders p WHERE f.idFolder=p.idFolder AND f.idFolder='%s'"%folderid)[0][0]
    for idchild in children:
        cpt = cpt+Request("SELECT count(*) FROM files f,folders p WHERE f.idFolder=p.idFolder AND f.idFolder='%s'"%idchild)[0][0]
    return cpt#Request("SELECT count(*) FROM files f,folders p WHERE f.idFolder=p.idFolder AND f.idFolder='%s'"%folderid)[0][0]

def count_pics_in_period(period,value):
    #   lister les images pour une date donnée
    formatstring = {"year":"%Y","month":"%Y-%m","date":"%Y-%m-%d","":"%Y"}[period]
    if period=="year" or period=="":
        if value:
            #filelist = search_between_dates( (value,formatstring) , ( str( int(value) +1 ),formatstring) )
            filelist = pics_for_period('year',value)
        else:
            filelist = search_all_dates()
    elif period in ["month","date"]:
        filelist = pics_for_period(period,value)

    else:
        #pas de periode, alors toutes les photos du 01/01 de la plus petite année, au 31/12 de la plus grande année
        listyears=get_years()
        amini=min(listyears)
        amaxi=max(listyears)
        if amini and amaxi:
            filelist = search_between_dates( ("%s"%(amini),formatstring) , ( "%s"%(amaxi),formatstring) )
        else:
            filelist = []
    return len(filelist)

"""
def list_cam_models():
    return [row for (row,) in Request('SELECT DISTINCT "Image Model" FROM files WHERE "Image Model" NOT NULL')]
"""

def list_path():
    """retourne la liste des chemins en base de données"""
    return [row for (row,) in Request( """SELECT DISTINCT strPath FROM files""" )]


def all_children_of_folder(rootid):
    """liste les id des dossiers enfants"""
    #A REVOIR : Ne fonctionne pas correctement !
    enfants=[]
    childrens=[rootid]
    #continu = False
    while True:
        try:
            _ = childrens.pop(0)
        except:
            #fin
            break
        chlist = [row for (row,) in Request( """SELECT idFolder FROM folders WHERE ParentFolder='%s'"""%id )]#2,10,17
        childrens=childrens+chlist
        enfants=enfants+chlist

    return enfants



#def search_between_dates(datestart='2007-01-01 00:00:01',dateend='2008-01-01 00:00:01'):
def search_between_dates(DateStart=("2007","%Y"),DateEnd=("2008","%Y")):
    """Cherche les photos qui ont été prises entre 'datestart' et 'dateend'."""
    common.log( "search_between_dates", DateStart)
    common.log( "search_between_dates", DateEnd)
    DS = strftime("%Y-%m-%d %H:%M:%S",strptime(DateStart[0],DateStart[1]))
    DE = strftime("%Y-%m-%d %H:%M:%S",strptime(DateEnd[0],DateEnd[1]))
    if DateEnd[1]=="%Y-%m-%d":
        Emodifier = "'start of day','+1 days','-1 minutes'"
        Smodifier = "'start of day'"
    elif DateEnd[1]=="%Y-%m":
        Emodifier = "'start of month','+1 months','-1 minutes'"
        Smodifier = "'start of month'"
    elif DateEnd[1]=="%Y":
        Emodifier = "'start of year','+1 years',-1 minutes'"
        Smodifier = "'start of year'"
    else:
        Emodifier = "''"
        Smodifier = "''"

    #SELECT strPath,strFilename FROM files WHERE strftime('%Y-%m-%d %H:%M:%S', "EXIF DateTimeOriginal") BETWEEN strftime('%Y-%m-%d %H:%M:%S','2007-01-01 00:00:01') AND strftime('%Y-%m-%d %H:%M:%S','2007-12-31 23:59:59') ORDER BY "EXIF DateTimeOriginal" ASC
    request = """SELECT strPath,strFilename FROM files WHERE datetime(ImageDateTime) BETWEEN datetime('%s',%s) AND datetime('%s',%s) ORDER BY ImageDateTime ASC"""%(DS,Smodifier,DE,Emodifier)
    return [row for row in Request(request)]

def pics_for_period(periodtype,date):

    try:
        sdate,modif1,modif2 = {'year' :['%s-01-01'%date,'start of year','+1 years'],
                               'month':['%s-01'%date,'start of month','+1 months'],
                               'date' :['%s'%date,'start of day','+1 days']}[periodtype]
    except:
        print_exc()
        #log ("pics_for_period ( periodtype = ['date'|'month'|'year'] , date = corresponding to the period (year|year-month|year-month-day)")
    request = """SELECT strPath,strFilename FROM files WHERE datetime(ImageDateTime) BETWEEN datetime('%s','%s') AND datetime('%s','%s','%s') ORDER BY ImageDateTime ASC;"""%(sdate,modif1,
                                                                                                                                                                                                  sdate,modif1,modif2)
    return [row for row in Request(request)]

def get_years():
    return [t for (t,) in Request("""SELECT DISTINCT strftime("%Y",ImageDateTime) FROM files where ImageDateTime NOT NULL ORDER BY ImageDateTime ASC""")]

def get_months(year):
    return [t for (t,) in Request("""SELECT distinct strftime("%%Y-%%m",ImageDateTime) FROM files where strftime("%%Y",ImageDateTime) = '%s' ORDER BY ImageDateTime ASC"""%year)]

def get_dates(year_month):
    return [t for (t,) in Request("""SELECT distinct strftime("%%Y-%%m-%%d",ImageDateTime) FROM files where strftime("%%Y-%%m",ImageDateTime) = '%s' ORDER BY ImageDateTime ASC"""%year_month)]

def search_all_dates():# TODO check if it is really usefull (check 'get_pics_dates' to see if it is not the same)
    """return all files from database sorted by 'EXIF DateTimeOriginal' """
    return [t for t in Request("""SELECT strPath,strFilename FROM files ORDER BY ImageDateTime ASC""")]

def get_pics_dates():
    """return all different dates from 'EXIF DateTimeOriginal'"""
    return [t for (t,) in Request("""SELECT DISTINCT strftime("%Y-%m-%d",ImageDateTime) FROM files WHERE length(trim(ImageDateTime))>0  ORDER BY ImageDateTime ASC""")]

def get_pic_date(path,filename):
    try:
        return [row for row in RequestWithBinds( """SELECT files.ImageDateTime FROM files WHERE strPath=? AND strFilename=? """,(path,filename) )][0][0]
    except IndexError:
        return None

if __name__=="__main__":
    pass

