#!/usr/bin/python

# python re-implementation of read10b.f  done by Danilo Banfi (danilo.banfi@cern.ch)
# This compute DA starting from the local .db produced by CreateDB.py
# Below are indicated thing that need to be edited by hand. 
# You only have to provide the name of the study <study_name> like 
# python CreateDB.py <write_your_fancy_study_name_here>
# DA result will be written in file DA_<study_name>.txt with the usual meaning for all seeds
# In file DA_<study_name>_summary.txt you will find study,angle,min,mean,max,nega,Amin,Amax of 
# lost1 , as in old .plot file
# 
# NOTA: please use python version >=2.6   

import sys
import getopt
from sixdesk import *
import numpy as np
import math
import matplotlib.pyplot as plt



# PART TO BE EDITED ========================================================================
Elhc=2.5                    #normalized emittance as in "general input"
Einj=7460.5                 #gamma as in "general input"
workarea='/afs/cern.ch/user/d/dbanfi/SixTrack_NEW'  #where input db is, and where output will be written
# DO NOT EDIT BEYOND HERE IF YOU'RE NOT REALLY SURE  =======================================    

rectype=[('study','S100'),('seed','int'),('betx'    ,'float'),('bety'    ,'float'),('sigx1'   ,'float'),('sigy1'   ,'float'),('emitx'   ,'float'),('emity'   ,'float'),
        ('sigxavgnld' ,'float') ,('sigyavgnld' ,'float'),('betx2'   ,'float'),('bety2'   ,'float'),('distp'   ,'float'),('dist'    ,'float'),
        ('sturns1' ,'int')   ,('sturns2' ,'int')  ,('turn_max','int')  ,('amp1'    ,'float'),('amp2'    ,'float'),('angle'   ,'float')]
names='study,seed,betx,bety,sigx1,sigy1,emitx,emity,sigxavgnld,sigyavgnld,betx2,bety2,distp,dist,sturns1,sturns2,turn_max,amp1,amp2,angle'
outtype=[('study','S100'),('seed','int'),('angle','float'),('achaos','float'),('achaos1','float'),('alost1','float'),('alost2','float'),('Amin','float'),('Amax','float')]

def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], "h", ["help"])
    except getopt.error, msg:
        print msg
        print "for help use --help"
        sys.exit(2)
    for o, a in opts:
        if o in ("-h", "--help"):
            print "use: DA_FullStat_public <study_name>"
            sys.exit(0)
    if len(args)<1 :
        print "too few options: please provide <study_name>"
        sys.exit()
    if len(args)>1 :
        print "too many options: please provide only <study_name>"
        sys.exit()
    
    database='%s/%s.db'%(workarea,args[0])
    if os.path.isfile(database):
        sd=SixDeskDB(database)
    else:
        print "ERROR: file  %s does not exists!" %(database)
        sys.exit()
    f = open('DA_%s.txt'%args[0], 'w')

    tmp=np.array(sd.execute('SELECT DISTINCT %s FROM results'%names),dtype=rectype)
    for angle in np.unique(tmp['angle']):
        for seed in np.unique(tmp['seed']):
            ich1 = 0
            ich2 = 0
            ich3 = 0
            icount = 1.
            itest = 0
            iin  = -999
            iend = -999
            alost1 = 0.
            alost2 = 0.
            achaos = 0
            achaos1 = 0
            mask=[(tmp['betx']>0) & (tmp['emitx']>0) & (tmp['bety']>0) & (tmp['emity']>0) & (tmp['angle']==angle) & (tmp['seed']==seed)]
            inp=tmp[mask]
            if inp.size<2 : 
                print 'not enought data for angle = %s' %angle
                break

            zero = 1e-10
            for itest in range(0,inp.size):
                if inp['betx'][itest]>zero and inp['emitx'][itest]>zero : inp['sigx1'][itest] =  math.sqrt(inp['betx'][itest]*inp['emitx'][itest]) 
                if inp['bety'][itest]>zero and inp['emity'][itest]>zero : inp['sigy1'][itest] =  math.sqrt(inp['bety'][itest]*inp['emity'][itest]) 
                if inp['betx'][itest]>zero and inp['emitx'][itest]>zero and inp['bety'][itest]>zero and inp['emity'][itest]>zero: itest+=1

            iel=inp.size-1
            rat=0

            if inp['sigx1'][0]>0:  
                rat=pow(inp['sigy1'][0],2)*inp['betx'][0]/(pow(inp['sigx1'][0],2)*inp['bety'][0])
            if pow(inp['sigx1'][0],2)*inp['bety'][0]<pow(inp['sigy1'][0],2)*inp['betx'][0]:
                rat=2        
            if inp['emity'][0]>inp['emitx'][0]:
                rat=0
                dummy=np.copy(inp['betx'])
                inp['betx']=inp['bety']
                inp['bety']=dummy
                dummy=np.copy(inp['betx2'])
                inp['betx2']=inp['bety2']
                inp['bety2']=dummy
                dummy=np.copy(inp['sigx1'])
                inp['sigx1']=inp['sigy1']
                inp['sigy1']=dummy
                dummy=np.copy(inp['sigxavgnld'])
                inp['sigxavgnld']=inp['sigyavgnld']
                inp['sigyavgnld']=dummy
                dummy=np.copy(inp['emitx']) 
                inp['emitx']=inp['emity']
                inp['emity']=dummy

            sigma=math.sqrt(inp['betx'][0]*Elhc/Einj)
            if abs(inp['emity'][0])>0 and abs(inp['sigx1'][0])>0:
                if abs(inp['emitx'][0])<zero :
                    rad=math.sqrt(1+(pow(inp['sigy1'][0],2)*inp['betx'][0])/(pow(inp['sigx1'][0],2)*inp['bety'][0]))/sigma
                else:
                    rad=math.sqrt((abs(inp['emitx'][0])+abs(inp['emity'][0]))/abs(inp['emitx'][0]))/sigma
            if abs(inp['sigxavgnld'][0])>zero and abs(inp['bety'][0])>zero:
                if abs(inp['emitx'][0]) < zero :
                    rad1=math.sqrt(1+(pow(inp['sigyavgnld'][0],2)*inp['betx'][0])/(pow(inp['sigxavgnld'][0],2)*inp['bety'][0]))/sigma
                else:
                    rad1=(inp['sigyavgnld'][0]*math.sqrt(inp['betx'][0])-inp['sigxavgnld'][0]*math.sqrt(inp['bety2'][0]))/(inp['sigxavgnld'][0]*math.sqrt(inp['bety'][0])-inp['sigyavgnld'][0]*math.sqrt(inp['betx2'][0]))
                    rad1=math.sqrt(1+rad1*rad1)/sigma
            else:
                rad1 = 1
            for i in range(0,iel+1):
                if ich1 == 0 and (inp['distp'][i] > 2. or inp['distp'][i]<=0.5):
                    ich1 = 1
                    achaos=rad*inp['sigx1'][i]
                    iin=i
                if ich3 == 0 and inp['dist'][i] > 1e-2 :
                    ich3=1
                    iend=i
                    achaos1=rad*inp['sigx1'][i]
                if ich2 == 0 and  (inp['sturns1'][i]<inp['turn_max'][i] or inp['sturns2'][i]<inp['turn_max'][i]):
                    ich2 = 1
                    alost2 = rad*inp['sigx1'][i]

            if iin != -999 and iend == -999 : iend=iel  
            if iin != -999 and iend >= iin :    
                for i in range(iin,iend+1) :
                    alost1 += (rad1/rad) * (inp['sigxavgnld'][i]/inp['sigx1'][i])
                alost1 = alost1/(float(iend)-iin+1)
                if alost1 >= 1.1 or alost1 <= 0.9:  alost1= -1. * alost1
            else:
                alost1 = 1.0
    
            alost1=alost1*alost2
            # print  "study=%s seed=%s angle = %s achaos= %s achaos1= %s alost1= %s alost2= %s rad*sigx1[1]= %s rad*sigx1[iel]= %s" %(args[0],seed,angle,achaos,achaos1,alost1,alost2,rad*inp['sigx1'][0],rad*inp['sigx1'][iel]) 
    
            f.write('%s %s %s %s %s %s %s %s %s \n'%(args[0],seed,angle,achaos,achaos1,alost1,alost2,rad*inp['sigx1'][0],rad*inp['sigx1'][iel]))
    f.close()


    f = open('DA_%s.txt'%args[0], 'r')
    final=np.genfromtxt(f,dtype=outtype)
    f.close()

    f1 = open('DA_%s_summary.txt'%args[0], 'w')

    for angle in np.unique(final['angle']):
        study=final['study'][0]
        mini = np.min(np.abs(final['alost1'][(final['angle']==angle)]))
        mean =np.mean(np.abs(final['alost1'][(final['angle']==angle)&(final['alost1']!=0)]))
        maxi = np.max(np.abs(final['alost1'][(final['angle']==angle)]))
        nega = len(final['alost1'][(final['angle']==angle)&(final['alost1']<0)])
        Amin = np.min(final['Amin'][final['angle']==angle])
        Amax = np.max(final['Amax'][final['angle']==angle])
        print study, angle, mini , mean, maxi,nega ,  Amin, Amax
        f1.write('%s %.2f %.2f %.2f %.2f %.0f %.2f %.2f \n'%(study,angle, mini , mean, maxi,nega ,  Amin, Amax))

    f1.close()    


if __name__ == "__main__":
    main()











