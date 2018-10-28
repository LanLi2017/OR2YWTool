import json
from io import StringIO
from itertools import groupby
from pprint import pprint


class WF:
    def __init__(self,params,inputlist,tablec=0,mass_editc=0,rename_c=0,textt_c=0,split_c=0,add_c=0,col_counter=0):
        self.parlist = inputlist
        self.params=params
        self.table_counter=tablec
        self.col_counter=col_counter
        self.mass_editc=mass_editc
        self.renamec=rename_c
        self.texttc=textt_c
        self.splitc=split_c
        self.addc=add_c

    def text_transform(self):
        col=self.params['columnName']
        expre=self.params['expression']
        columnnName='col-name:{}'.format(col)
        expression='expression:{}'.format(expre)
        self.parlist.extend([columnnName,expression])
        self.col_counter+=1
        self.texttc+=1
        outname='col:{}{}'.format(col,self.col_counter)
        return outname

    def rename(self):
        oldcol=self.params['oldColumnName']
        newcol=self.params['newColumnName']
        oldcol_name='oldColumnName:{}'.format(oldcol)
        newcol_name='newColumnName:{}'.format(newcol)
        self.parlist.extend([oldcol_name,newcol_name])
        self.table_counter+=1
        self.renamec+=1
        outname='table{}'.format(self.table_counter)
        return outname

    def addition(self):
        newcol=self.params['newColumnName']
        basecol=self.params['baseColumnName']
        colInsert=self.params['columnInsertIndex']
        expre=self.params['expression']
        newcol_name='newColumnName:{}'.format(newcol)
        basecol_name='baseColumnName:{}'.format(basecol)
        colInsert_index='columnInsertIndex:{}'.format(colInsert)
        expression='expression:{}'.format(expre)
        self.parlist.extend([newcol_name,basecol_name,colInsert_index,expression])
        self.table_counter+=1
        self.addc+=1
        outname='table{}'.format(self.table_counter)
        return outname

    def split(self):
        col=self.params['columnName']
        removeOR=self.params['removeOriginalColumn']
        separ=self.params['separator']
        col_name='col-name:{}'.format(col)
        removeor='removeOriginalColumn:{}'.format(removeOR)
        separator='separator:{}'.format(separ)
        self.parlist.extend([col_name,removeor,separator])
        self.table_counter+=1
        self.splitc+=1
        outname='table{}'.format(self.table_counter)
        return outname

    def mass_edit(self):
        col=self.params['columnName']
        expre=self.params['expression']
#         edits=self.params['']
        col_name='col-name:{}'.format(col)
        expression='expression:{}'.format(expre)
        self.parlist.extend([col_name,expression])
        self.col_counter+=1
        self.mass_editc+=1
        outname='col:{}{}'.format(col,self.col_counter)
        return outname


def add_dependency(wf):
    for i in range(len(wf)):
        # print(i)
        if any([wf[i]['op']=='core/text-transform',wf[i]['op']=='core/mass-edit']):
            wf[i]['dependency']=wf[i]['columnName']

        elif wf[i]['op']=='core/column-rename':
            if 'dependency' not in wf[i]:
                wf[i]['dependency']=wf[i]['oldColumnName'].split()[0]
            for j in range(i+1,len(wf)):
                if wf[j]['op']=='core/column-addition':
                    if wf[j]['baseColumnName']==wf[i]['newColumnName']:
                        wf[j]['dependency']=wf[i]['oldColumnName']
                elif wf[j]['op']=='core/column-rename':
                    if any([wf[j]['oldColumnName']==wf[i]['newColumnName'],wf[j]['newColumnName']==wf[i]['oldColumnName']]):
                        wf[j]['dependency']=wf[i]['dependency']
                else:
                    if wf[j]['columnName'].split()[0]==wf[i]['newColumnName']:
                        wf[j]['dependency']=wf[i]['dependency']
        elif wf[i]['op']=='core/column-addition':
            if 'dependency' not in wf[i]:
                wf[i]['dependency']=wf[i]['baseColumnName'].split()[0]
            for j in range(i+1,len(wf)):
                if wf[j]['op']=='core/column-addition':
                    if wf[j]['baseColumnName']==wf[i]['newColumnName']:
                        wf[j]['dependency']=wf[i]['dependency']
                elif wf[j]['op']=='core/column-rename':
                    if any([wf[j]['oldColumnName']==wf[i]['newColumnName'],wf[j]['oldColumnName']==wf[i]['baseColumnName']]):
                        wf[j]['dependency']=wf[i]['dependency']
                else:
                    if any([wf[j]['columnName'].split()[0]==wf[i]['baseColumnName'],wf[j]['columnName'].split()[0]==wf[i]['newColumnName']]):
                        wf[j]['dependency']=wf[i]['dependency']
        elif wf[i]['op']=='core/column-split':
            if 'dependency' not in wf[i]:
                wf[i]['dependency']=wf[i]['columnName'].split()[0]
            for j in range(i+1,len(wf)):
                if wf[j]['op']=='core/column-addition':
                    if wf[j]['baseColumnName'].split()[0]==wf[i]['columnName'].split()[0]:
                        wf[j]['dependency']=wf[i]['dependency']
                elif wf[j]['op']=='core/column-rename':
                    if wf[j]['oldColumnName'].split()[0]==wf[i]['columnName'].split()[0]:
                        wf[j]['dependency']=wf[i]['dependency']
                else:
                    if wf[j]['columnName'].split()[0]==wf[i]['columnName'].split()[0]:
                        wf[j]['dependency']=wf[i]['dependency']
    return wf


def getInputlist(params,tablec,inputl):
    wf=WF(params,inputl,tablec)
    if params['op']=='core/column-rename':
        wf.rename()
    elif params['op']=='core/column-addition':
        wf.addition()
    elif params['op']=='core/column-split':
        wf.split()
    elif params['op']=='core/text-transform':
        wf.text_transform()
    elif params['op']=='core/mass-edit':
        wf.mass_edit()
    inputlist=wf.parlist
    table_counter=wf.table_counter
    return inputlist,table_counter


def ruleforinput(ind,outname):
    if ind==0:
        in_name='table0'

    else:
        in_name='{}'.format(outname)
    return in_name


def writeheader(title,description,inputlist,table_counter,yw):
    f=StringIO()
    f.write('#@begin {} #@desc {}\n'.format(title,description))
    for sublist in inputlist:
        f.write('#@param {}\n'.format(sublist))
    f.write('#@in table0\n')
    f.write('#@out table{}\n'.format(table_counter+1))
    # write contents
    tablec=0
    massedit_c=0
    texttransform_c=0
    split_c=0
    rename_c=0
    add_c=0
    inputl=[]
    outputnamelist=[]
    for innerlist in yw:
        ind=0
        outputname=''
        col_counter=0
        for innerdicts in innerlist:
            wf=WF(innerdicts,inputl,tablec,massedit_c,rename_c,texttransform_c,split_c,add_c,col_counter)
            if innerdicts['op']=='core/column-rename':
                outname=wf.rename()
                print('rename',outname)
                f.write('#@begin {}{} #@desc {}\n'.format(innerdicts['op'],rename_c,innerdicts['description']))
                f.write('#@param oldColumnName:{}\n'.format(innerdicts['oldColumnName']))
                f.write('#@param newColumnName:{}\n'.format(innerdicts['newColumnName']))
                in_name=ruleforinput(ind,outputname)
                f.write('#@in {}\n'.format(in_name))
                f.write('#@out {}\n'.format(outname))
                f.write('#@end {}{}\n'.format(innerdicts['op'],rename_c))
                ind+=1
                outputname=outname
            elif innerdicts['op']=='core/column-addition':
                outname=wf.addition()
                print('add',outname)
                f.write('#@begin {}{} #@desc {}\n'.format(innerdicts['op'],add_c,innerdicts['description']))
                f.write('#@param baseColumnName:{}\n'.format(innerdicts['baseColumnName']))
                f.write('#@param columnInsertIndex:{}\n'.format(innerdicts['columnInsertIndex']))
                f.write('#@param newColumnName:{}\n'.format(innerdicts['newColumnName']))
                in_name=ruleforinput(ind,outputname)
                f.write('#@in {}\n'.format(in_name))
                f.write('#@out {}\n'.format(outname))
                f.write('#@end {}{}\n'.format(innerdicts['op'],add_c))
                ind+=1
                outputname=outname
            elif innerdicts['op']=='core/column-split':
                outname=wf.split()
                print('split',outname)
                f.write('#@begin {}{} #@desc {}\n'.format(innerdicts['op'],split_c,innerdicts['description']))
                f.write('#@param col-name:{}\n'.format(innerdicts['columnName']))
                f.write('#@param removeOriginalColumn:{}\n'.format(innerdicts['removeOriginalColumn']))
                f.write('#@param separator:{}\n'.format(innerdicts['separator']))
                in_name=ruleforinput(ind,outputname)
                f.write('#@in {}\n'.format(in_name))
                f.write('#@out {}\n'.format(outname))
                f.write('#@end {}{}\n'.format(innerdicts['op'],split_c))
                ind+=1
                outputname=outname
            elif innerdicts['op']=='core/text-transform':
                outname=wf.text_transform()
                f.write('#@begin {}{} #@desc {}\n'.format(innerdicts['op'],texttransform_c,innerdicts['description']))
                f.write('#@param col-name:{}\n'.format(innerdicts['columnName']))
                f.write('#@param expression:{}\n'.format(innerdicts['expression']))
                in_name=ruleforinput(ind,outputname)
                f.write('#@in {}\n'.format(in_name))
                f.write('#@out {}\n'.format(outname))
                f.write('#@end {}{}\n'.format(innerdicts['op'],texttransform_c))
                ind+=1
                outputname=outname
            elif innerdicts['op']=='core/mass-edit':
                outname=wf.mass_edit()
                f.write('#@begin {}{} #@desc {}\n'.format(innerdicts['op'],massedit_c,innerdicts['description']))
                f.write('#@param col-name:{}\n'.format(innerdicts['columnName']))
                in_name=ruleforinput(ind,outputname)
                f.write('#@in {}\n'.format(in_name))
                f.write('#@out {}\n'.format(outname))
                f.write('#@end {}{}\n'.format(innerdicts['op'],massedit_c))
                ind+=1
                outputname=outname
            col_counter=wf.col_counter
            tablec=wf.table_counter
            massedit_c=wf.mass_editc
            rename_c=wf.renamec
            texttransform_c=wf.texttc
            split_c=wf.splitc
            add_c=wf.addc
        outputnamelist.append(outputname)
    # merge:
    print(outputnamelist)
    f.write('#@begin MergeOperationsColumns #@desc Merge the Parallel Column operations\n')
    for out_name in outputnamelist:
        f.write('#@in {}\n'.format(out_name))

    f.write('#@out table{}\n'.format(table_counter+1))
    f.write('#@end MergeOperationsColumns\n')

    f.write('#@end {}\n'.format(title))
    output_string=f.getvalue()
    f.close()

    return output_string


def main():
    with open('wf.json')as f:
        data=json.load(f)

    tablec=0
    inputlist=[]
    for datadicts in data:
        inputlist=getInputlist(datadicts,tablec,inputlist)[0]
        tablec=getInputlist(datadicts,tablec,inputlist)[1]
    inputlist=list(set(inputlist))
    schema=['core/column-rename','core/column-addition','core/column-split']
    column=['core/text-transform','core/mass-edit']

    # begin name:  params["op"]
    #  columnName,  newColumnName,  baseColumnName, baseColumnName
    # {'column A name': [],   'column B name': []}

    dependencydicts={}
    dependencydata=add_dependency(data)
    # group them according to the dependency
    for dicts in dependencydata:
        dependencydicts.setdefault(dicts['dependency'],[]).append(dicts)
    pprint(dependencydicts)
    ywdicts=dependencydicts.values()

    result=writeheader(title='Parallel_test',description='this is to test the new code',inputlist=inputlist,table_counter=tablec,yw=ywdicts)
    print(result)

    # write in yw text
    f=StringIO()
    f.writelines('#beging ')






if __name__=='__main__':
    main()


