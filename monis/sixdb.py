import sqlite3,time
import psutil, os, re, gzip
from sys import platform as _platform
import sys
import sixdeskdir

def col_count(cur,table):
    sql = 'pragma table_info(%s)'%(table)
    cur.execute(sql)
    return len(cur.fetchall())

def dict_to_list(dict):
    lst = []
    for i in sorted(dict.keys()):
        for j in dict[i]:
            if isinstance(j,list):
                lst.append(j)
            else:
                lst.append(dict[i])
                break
    return lst

def store_dict(cur,colName,table,data):
    cur.execute("select max(%s) from %s"% (colName,table))
    temp = cur.fetchone()[0]
    if temp is not None:
        newid = int(temp) + 1
    else:   
        newid = 1
    lst = []
    for head in data:
      lst.append([newid,head,data[head]])
    sql = "INSERT into %s values(?,?,?)"%(table)
    cur.executemany(sql,lst)
    return newid

def load_dict(cur,table,idcol,idnum):
    sql='SELECT key,value from %s WHERE %s=%d'%(table,idcol,idnum)
    cur.execute(sql)
    a = cur.fetchall()
    dict = {}
    for row in a:
        dict[str(row[0])] = str(row[1]) 
    return dict 

class SixDB(object):
    file = []

    def __init__(self,studyDir):
        self.studyDir = studyDir
        self.env_var = sixdeskdir.parse_env(studyDir)
        db = self.env_var['LHCDescrip']+".db"
        self.conn = sqlite3.connect(db,isolation_level="IMMEDIATE")
        print "Opened database successfully"
        self.create_empty_tables()

    def create_empty_tables(self):
        env_var = self.env_var
        conn = self.conn
        cur = conn.cursor() 
        sql = """CREATE table if not exists env(env_id int, key string, 
            value string)"""
        cur.execute(sql)

        sql = """create table if not exists mad6t_run(env_id int, run_id string,
        seed int , mad_in blob, mad_out blob, mad_lsf blob)"""
        cur.execute(sql)

        sql = """create table if not exists mad6t_run2(env_id int, 
            fort3aux blob, fort3mad blob, fort3mother1 blob, 
            fort3mother2 blob)"""
        cur.execute(sql)

        sql = """create table if not exists mad6t_results(env_id int, seed int,
            fort2 blob, fort8 blob, fort16 blob)"""
        cur.execute(sql)

        sql = """create table if not exists six_beta(env_id int, seed int, 
            tunex double, tuney double, beta11 double, beta12 double, 
            beta22 double, beta21 double, qx double,qy double,dqx double, 
            dqy double, x double, xp double,y double, yp double, sigma double, 
            delta double, emitn double, gamma double, deltap double, qx1 double,
             qy1 double, qx2 double, qy2 double)"""
        cur.execute(sql)

        sql = """create table if not exists six_input(id integer primary key,
            env_id int, seed int, simul string, tunex double, tuney double, 
            amp1 int, amp2 int, turns string, angle int, fort3 blob)"""
        cur.execute(sql)
        
        sql = """create table if not exists six_results(six_input_id int, 
            row_num int, """
            +','.join('o'+str(i)+' double' for i in xrange(1,61)) + 
            """, primary key(six_input_id,row_num))"""
        cur.execute(sql)

        sql = """create table if not exists files(env_id int, path text, 
            content blob)"""
        cur.execute(sql)
        cur.execute("PRAGMA synchronous = OFF")
        cur.execute("PRAGMA journal_mode = MEMORY")
        cur.execute("PRAGMA auto_vacuum = FULL")
        cur.execute("PRAGMA temp_store = MEMORY")
        cur.execute("PRAGMA count_changes = OFF")   
        cur.execute("PRAGMA mmap_size=2335345345")

    def st_control(self):
        cur = self.conn.cursor()    
        env_var = self.env_var
        workdir = env_var['sixdeskhome']
        #workdir = os.path.join(
        #    env_var['scratchdir'],env_var['workspace'],'sixjobs')
        print workdir
        #env_var['sixdesktrack'] += '/'+env_var['LHCDescrip']
        print env_var['sixdesktrack']
        print env_var['sixtrack_input']
        cur.execute("SELECT max(env_id) from env")
        temp = cur.fetchone()[0]
        if temp is not None:
            newid = int(temp) + 1
        else:   
            newid = 1
        self.newid = newid
        beam = env_var['beam']
        if beam == "" or beam == "b1" or beam == "B1":
            appendbeam = ""
        elif beam == "b2" or beam == "B2":
            appendbeam = "_b2"
        else:
            print 'Unrecognised beam option must be null,b1,B1,b2 or B2'
            return
        files = 'fort.3.mother2_'+str(env_var['runtype'])+appendbeam
        path = os.path.join(workdir,'control_files',files)
        content = sqlite3.Binary(open(path,'r').read())
        self.file.append([newid,path,content])

    def st_mask(self):
        env_var = self.env_var
        newid = self.newid
        workdir = env_var['sixdeskhome']
        files = str(env_var['LHCDescrip'])+'.mask'
        path = os.path.join(workdir,'mask',files)
        content = sqlite3.Binary(open(path,'r').read())
        self.file.append([newid,path,content])

    def st_env(self):
        cur = self.conn.cursor()
        env_var = self.env_var
        workdir = env_var['sixdeskhome']
        flag = 0
        for dirName, subdirList, fileList in os.walk(workdir+'/studies'):
            for files in fileList:
                if ('sixdeskenv' in files or 'sysenv' in files) and flag == 0:
                    #env_var = sixdeskenvdir.parse_env(dirName)
                    self.newid = store_dict(cur,"env_id","env",env_var)
                    self.conn.commit()
                    flag = 1
                path = os.path.join(dirName,files)
                content = sqlite3.Binary(open(path,'r').read())
                self.file.append([self.newid,path,content])

    def st_mad6t_run(self):
        conn = self.conn
        cur = conn.cursor()
        env_var = self.env_var
        newid = self.newid
        rows = {}
        #print newid
        col = col_count(cur,'mad6t_run')
        for dirName, subdirList, fileList in os.walk(env_var['sixtrack_input']):
            if 'mad.dorun' in dirName:
                for files in fileList:
                    if not ( files.endswith('.mask') or 'out' in files 
                            or files.endswith('log') or files.endswith('lsf') ):
                        seed = files.split('.')[-1]
                        run_id = dirName.split('/')[-1]
                        mad_in = sqlite3.Binary(open(
                            os.path.join(dirName,files),'r'
                                                    ).read()
                                                )

                        out_file = files.replace('.','.out.')
                        mad_out = sqlite3.Binary(open(
                            os.path.join(dirName,out_file),'r'
                                                    ).read()
                                                )
                        lsf_file = 'mad6t_'+seed+'.lsf'
                        mad_lsf = sqlite3.Binary(open(
                            os.path.join(dirName,lsf_file),'r'
                                                    ).read()
                                                )
                        rows[seed] = []
                        rows[seed].append([newid,run_id,seed,mad_in,mad_out,
                                            mad_lsf])
                    if files.endswith('.log'):
                        path = os.path.join(dirName,files)
                        content = sqlite3.Binary(open(path,'r').read())
                        self.file.append([newid,path,content])
            if rows:
                lst = dict_to_list(rows)
                sql = "INSERT into mad6t_run values(" 
                sql += ','.join("?"*col) + ")"
                cur.executemany(sql,lst)
                conn.commit()
                rows = {}
        if self.file:
            sql = "INSERT into files values (?,?,?)"
            cur.execute("begin IMMEDIATE transaction")
            cur.executemany(sql,self.file)
            conn.commit()
            self.file = []

    def st_mad6t_run2(self):
        conn = self.conn
        cur = conn.cursor()
        env_var = self.env_var
        newid = self.newid
        workdir = env_var['sixtrack_input']
        fort3 = {}
        #print newid
        col = col_count(cur,'mad6t_run2')
        for dirName, subdirList, fileList in os.walk(workdir):
            for files in fileList:
                if 'fort.3' in files and not files.endswith('.tmp'):
                    fort3[files.replace('fort.3.','')] = sqlite3.Binary(open(
                            os.path.join(dirName,files),'r'
                                                      ).read()
                                                                    )
                if files.endswith('.tmp'):
                    path = os.path.join(dirName,files)
                    content = sqlite3.Binary(open(path,'r').read())
                    self.file.append([newid,path,content])
            if fort3 and len(fort3.keys()) == 4:
                sql = "INSERT into mad6t_run2 values(" + ','.join("?"*col) + ")"
                cur.execute(sql,[newid,fort3['aux'],fort3['mad'],
                                fort3['mother1'],fort3['mother2']
                                ]
                            )
                conn.commit()
                fort3 = {}
        if self.file:
            sql = "INSERT into files values (?,?,?)"
            cur.execute("begin IMMEDIATE transaction")
            cur.executemany(sql,self.file)
            self.file = []

    def st_mad6t_results(self):
        conn = self.conn
        cur = conn.cursor()
        env_var = self.env_var
        newid = self.newid
        workdir = env_var['sixtrack_input']
        rows = {}
        col = col_count(cur,'mad6t_results')
        for dirName, subdirList, fileList in os.walk(workdir):
            for files in fileList:
                if 'fort' in files and files.endswith('.gz'):
                    head = int(files.split('_')[1].replace('.gz',''))
                    if head not in rows.keys():
                        rows[head] = [newid,head]
                    if '2' in files:
                        rows[head].insert(2,sqlite3.Binary(gzip.open(
                                            os.path.join(dirName,files),'r'
                                                        ).read()
                                                        )
                                        )
                    elif '8' in files:
                        rows[head].insert(3,sqlite3.Binary(gzip.open(
                                            os.path.join(dirName,files),'r'
                                                        ).read()
                                                        )
                                        )
                    else:
                        rows[head].extend([sqlite3.Binary(gzip.open(
                                            os.path.join(dirName,files),'r'
                                                        ).read()
                                                        )
                                        ])
            if rows:
                lst = dict_to_list(rows)
                sql = "INSERT into mad6t_results values(" + ','.join("?"*col) 
                sql += ")"
                cur.execute("begin IMMEDIATE transaction")
                cur.executemany(sql,lst)
                conn.commit()
                rows = {}

    def st_six_beta(self):
        conn = self.conn
        cur = conn.cursor()
        env_var = self.env_var
        newid = self.newid
        rows = {}
        col = col_count(cur,'six_beta')
        beta = six = gen = []
        for dirName, subdirList, fileList in os.walk(env_var['sixdesktrack']):
            for files in fileList:
                if 'general_input' in files:
                    with open(os.path.join(dirName,files),'r') as FileObj:
                        for lines in FileObj:
                            gen = lines.split()
                    path = os.path.join(dirName,files)
                    content = sqlite3.Binary(open(path,'r').read())
                    self.file.append([newid,path,content])
                if 'betavalues' in files or 'sixdesktunes' in files:
                    dirn = dirName.replace(env_var['sixdesktrack']+'/','')
                    dirn = dirn.split('/')
                    seed = int(dirn[0])
                    tunex,tuney = [i for i in dirn[2].split('_')]
                    if not seed in rows.keys():
                        rows[seed] = []
                    temp = [newid,seed,tunex,tuney]
                    if 'betavalues' in files:
                        f = open(os.path.join(dirName,files),'r')
                        beta = [float(i) for i in f.read().split()]
                    if 'sixdesktunes' in files:
                        f = open(os.path.join(dirName,files),'r')
                        six = [float(i) for i in f.read().split()]
                    f.close()
                if beta and temp and six:
                    rows[seed].append(temp+beta+gen+six)
                    beta = temp = six = []
            
            if rows:
                lst = dict_to_list(rows)
                sql = "INSERT into six_beta values(" + ','.join("?"*col) + ")"
                cur.executemany(sql,lst)
                conn.commit()
                rows = {}

    def st_six_input_results(self):
        conn = self.conn
        cur = conn.cursor()
        env_var = self.env_var
        newid = self.newid
        rows = []
        res = []
        cur.execute('SELECT id from six_input order by id DESC limit 1')
        six_id = cur.fetchone()
        if six_id is not None:
            six_id += 1
        else:
            six_id = 1
        col = col_count(cur,'six_input')
        col1 = col_count(cur,'six_results')
        for dirName, subdirList, fileList in os.walk(env_var['sixdesktrack']):
            for files in fileList:
                if 'fort.3' in files and not '-' in dirName:
                    dirn = dirName.replace(env_var['sixdesktrack']+'/','')
                    #print dirn
                    dirn = re.split('/|_',dirn)
                    dirn = [six_id,newid] + dirn
                    dirn.extend([sqlite3.Binary(gzip.open(
                                            os.path.join(dirName,files),'r'
                                                ).read()
                                            )])
                    rows.append(dirn)               
                    dirn=[]
                    files = files.replace('3','10')
                    with gzip.open(os.path.join(dirName,files),"r") as FileObj:
                        count = 1
                        for lines in FileObj:
                            res.append([six_id,count]+lines.split())
                            count += 1
                    six_id += 1
                if files.endswith('.log') or files.endswith('.lsf'):
                    path = os.path.join(dirName,files)
                    content = sqlite3.Binary(open(path,'r').read())
                    self.file.append([newid,path,content])
            if len(rows) > 3000:
                sql = "INSERT into six_input values (" 
                sql += ','.join('?'*col) + ")"
                cur.execute("begin IMMEDIATE transaction")
                cur.executemany(sql,rows)
                conn.commit()
                rows = []
            if len(res) > 90000:
                sql = "INSERT into six_results values (" 
                sql += ','.join('?'*col1) + ")"
                cur.execute("begin IMMEDIATE transaction")
                cur.executemany(sql,res)
                conn.commit()
                res = []
        if rows:
            sql = "INSERT into six_input values (" + ','.join('?'*col) + ")"
            cur.executemany(sql,rows)
            conn.commit()
            rows = []
        if res:
            sql = "INSERT into six_results values (" + ','.join('?'*col1) + ")"
            cur.execute("begin IMMEDIATE transaction")
            cur.executemany(sql,res)
            conn.commit()
            res = []
        if self.file:
            sql = "INSERT into files values (?,?,?)"
            cur.execute("begin IMMEDIATE transaction")
            cur.executemany(sql,self.file)
            conn.commit()
            self.file = []

class SixDir(object):
    file = []
    def __init__(self,studyName):
        self.studyName = studyName
        if not os.path.isfile(studyName+'.db'):
            print "study does'nt exist in DB"
            return
        try:
            db = studyName+".db"
            conn = sqlite3.connect(db,isolation_level="IMMEDIATE")
        except sqlite3.Error:
            print 'error'
            return
        print "Opened database successfully"
        self.conn = conn
        self.load_env_var()

    def load_env_var(self):
        conn = self.conn
        cur = conn.cursor()
        sql = """SELECT env_id from env where key='LHCDescrip' and value='%s'"""
        cur.execute(sql%self.studyName)
        temp = cur.fetchone()[0]
        if temp is not None:
            id = int(temp)
        else:   
            'studyname not found'
            return
        self.env_var = load_dict(cur,"env","env_id",id)
        self.id = id

    def load_extra(self):
        conn = self.conn
        cur = conn.cursor()
        env_var = self.env_var
        id = self.id
        cur.execute("begin IMMEDIATE transaction")
        sql = """SELECT path,content from files where env_id = ?"""
        cur.execute(sql,[id])
        files = cur.fetchall()
        #print len(files)
        for file in files:
            path = os.path.dirname(str(file[0]))
            if not os.path.exists(path):
                os.makedirs(path)
            if not 'gz' in str(file[0]):
                f = open(str(file[0]),'w')
            else:
                f = gzip.open(str(file[0]),'w')
            f.write(str(file[1]))
            f.close()

    def load_mad6t_run(self):
        conn = self.conn
        cur = conn.cursor()
        env_var = self.env_var
        id = self.id
        sql = """SELECT * from mad6t_run where env_id = ?"""
        cur.execute(sql,[id])
        files = cur.fetchall()
        for file in files:
            path = os.path.join(env_var['sixtrack_input'],str(file[1]))
            if not os.path.exists(path):
                    os.makedirs(path)
            mad_in,mad_out,mad_lsf = [str(file[i]) for i in range(3,6)]
            f = open(path+'/'+env_var['LHCDescrip']+'.'+str(file[2]),'w')
            f.write(mad_in)
            f = open(path+'/'+env_var['LHCDescrip']+'.out.'+str(file[2]),'w')
            f.write(mad_out)
            f = open(path+'/mad6t_'+str(file[2])+'.lsf','w')
            f.write(mad_lsf)
        f.close()

    def load_mad6t_run2(self):
        conn = self.conn
        cur = conn.cursor()
        env_var = self.env_var
        id = self.id
        sql = """SELECT * from mad6t_run2 where env_id = ?"""
        cur.execute(sql,[id])
        fort3 = cur.fetchone()
        aux,mad,m1,m2 = [str(fort3[i]) for i in range(1,5)]
        path = env_var['sixtrack_input']
        f = open(path+'/fort.3.aux','w')
        f.write(aux)
        f = open(path+'/fort.3.mad','w')
        f.write(mad)
        f = open(path+'/fort.3.mother1','w')
        f.write(m1)
        f = open(path+'/fort.3.mother2','w')
        f.write(m2)
        f.close()

    def load_mad6t_results(self):
        conn = self.conn
        cur = conn.cursor()
        env_var = self.env_var
        id = self.id
        cur.execute("begin IMMEDIATE transaction")
        sql = """SELECT * from mad6t_results where env_id = ?"""
        cur.execute(sql,[id])
        forts = cur.fetchall()
        path = env_var['sixtrack_input']
        for fort in forts:
            seed,f2,f8,f16 = [str(fort[i]) for i in range(1,5)]
            f = gzip.open(path+'/fort.2_'+seed+'.gz','w')
            f.write(f2)
            f = gzip.open(path+'/fort.8_'+seed+'.gz','w')
            f.write(f8)
            f = gzip.open(path+'/fort.16_'+seed+'.gz','w')
            f.write(f16)
        f.close()

    def load_six_beta(self):
        conn = self.conn
        cur = conn.cursor()
        env_var = self.env_var
        id = self.id
        path = env_var['sixdesktrack']
        cur.execute("begin IMMEDIATE transaction")
        sql = """SELECT * from six_beta where env_id = ?"""
        cur.execute(sql,[id])
        beta = cur.fetchall()
        for row in beta:
            sql = """SELECT simul from six_input where env_id=? and seed=? and 
                    tunex=? and tuney=?"""
            cur.execute(sql,row[0:4])
            simul = cur.fetchone()[0]
            path1 = os.path.join(
                path,str(row[1]),simul,str(row[2])+'_'+str(row[3])
                )
            if not os.path.exists(path1):
                os.makedirs(path1)
            stri = ' '.join([str(row[i]) for i in range(5,19)])
            f = open(path1+'/betavalues','w')
            f.write(stri)
            stri = str(row[11])+' '+str(row[12])
            f = open(path1+'/mychrom','w')
            f.write(stri)
            stri = str(row[20])+'\n'+str(row[21])+' '+str(row[22])+'\n'
            stri += str(row[23])+' '+str(row[24])
            f = open(path1+'/sixdesktunes','w')
            f.write(stri)
        f.close()

    def load_six_input_results(self):
        conn = self.conn
        cur = conn.cursor()
        env_var = self.env_var
        id = self.id
        path = env_var['sixdesktrack']
        cur.execute("begin IMMEDIATE transaction")
        sql = """SELECT * from six_input where env_id=?"""
        cur.execute(sql,[id])
        six = cur.fetchall()
        for row in six:
            path1 = os.path.join(
                path,str(row[2]),str(row[3]),str(row[4])+'_'+str(row[5]),
                str(row[6])+'_'+str(row[7]),str(row[8]),str(row[9])
                )
            if not os.path.exists(path1):
                os.makedirs(path1)
            f = gzip.open(path1+'/fort.3.gz','w')
            f.write(str(row[10]))
            sql = """SELECT * from six_results where six_input_id=?"""
            cur.execute(sql,[row[0]])
            fort = cur.fetchall()
            stri = ""
            for col in fort:
                str1 = ""
                for i in xrange(60):
                    str1 += str(col[i+2]) + ' '
                stri += str1 + '\n'
            f = gzip.open(path1+'/fort.10.gz','w')
            f.write(stri)
            f.close()

    def join10(self):
        conn = self.conn
        cur = conn.cursor()
        env_var = self.env_var
        id = self.id
        ista = int(env_var['ista'])
        iend = int(env_var['iend'])
        tuney = float(env_var['tuney'])
        tunex = float(env_var['tunex'])
        tune = str(tunex)+'_'+str(tuney)
        print env_var['short'],env_var['long']
        if env_var['short'] == 1:
            amp1 = int(env_var['ns1s'])
            amp2 = int(env_var['ns2s'])
            ampd = int(env_var['nss'])
        else:
            amp1 = int(env_var['ns1l'])
            amp2 = int(env_var['ns2l'])
            ampd = int(env_var['nsincl'])
        sql = """SELECT distinct turns,angle from six_input"""
        cur.execute(sql)
        val = cur.fetchall()
        for seed in range(ista,iend+1):
            workdir = os.path.join(
                env_var['sixdesktrack'],str(seed),'simul',tune
                )
            join = os.path.join(workdir,str(amp1)+'-'+str(amp2))
            #print join
            for amp in range(amp1,amp2,ampd):
                sql = """SELECT * from six_input,six_results 
                where six_input_id=id and seed=? and amp1=? and amp2=? 
                and env_id=?"""
                cur.execute(sql,[seed,amp,amp+2,id])
                data = cur.fetchall()
                while data:
                    path = os.path.join(join,str(data[0][8]),str(data[0][9]))
                    if not os.path.exists(path):
                        os.makedirs(path)
                    if amp == amp1:
                        f = gzip.open(os.path.join(path,'fort.10.gz'),'w')
                        #print os.path.join(path,'fort.10.gz')
                    else:
                        f = gzip.open(os.path.join(path,'fort.10.gz'),'a')
                    for j in xrange(30):
                        str1 = '\t'.join(
                            [str(data[0][i]) for i in range(13,73)]
                            )
                        str1 += '\n'
                        f.write(str1)
                        del data[0]
                    f.close()


if __name__ == '__main__':
    # a = SixDB('./files/w7/sixjobs/')
    # a.st_control()
    # a.st_mask()
    # a.st_env()
    # a.st_mad6t_run()
    # a.st_mad6t_run2()
    # a.st_mad6t_results()
    # a.st_six_beta()
    # a.st_six_input_results()
    # a = SixDir('jobslhc31b_inj55_itv19')
    # a.load_extra()
    # a.load_mad6t_run()
    # a.load_mad6t_run2()
    # a.load_mad6t_results()
    # a.load_six_beta()
    # a.load_six_input_results()
    # a.join10()
