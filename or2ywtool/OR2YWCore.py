# import all library needed for this class
import json
import re
from collections import Counter

from itertools import groupby
from io import StringIO
import sys
import argparse;
import os
import uuid
import subprocess


class FileHelper:
    def __init__(self):
        pass

    @staticmethod
    def is_tool(name):
        from distutils.spawn import find_executable
        return find_executable(name) is not None


def addition_dependency(params):
    # two kinds of expressions :
    # 1. the column name has space: "grel:cells[\"Sponsor 2\"].value + cells[\"Sponsor 7\"].value"  : [A-Z]\w+ \d
    # 2. the column name does not have space: "grel:cells.name.value + cells.event.value" :   \.\w+\.
    #  normal one: "grel:value"
    exp=params['expression']
    res=params['baseColumnName'].replace(" ", "_")
    if exp=='"grel:value"':
    #      missing information here: if no merge other columns, we still do not know if the new column is set
    # --------dependency as basecolumnName
       result=res
       return result
    result=re.findall('\.\w+\.',exp)
    if result:
        return result
    else:
        return re.findall('[A-Z]\w+ \d',exp)


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
        col=(self.params['columnName']).replace(" ", "_")
        expre=self.params['expression']
        columnnName='col-name:{}'.format(col)
        expression='expression:{}'.format(expre)
        self.parlist.extend([columnnName,expression])
        self.col_counter+=1
        self.texttc+=1
        outname='col:{}{}'.format(col,self.col_counter)
        return outname

    def rename(self):
        oldcol=(self.params['oldColumnName']).replace(" ", "_")
        newcol=(self.params['newColumnName']).replace(" ", "_")
        oldcol_name='oldColumnName:{}'.format(oldcol)
        newcol_name='newColumnName:{}'.format(newcol)
        self.parlist.extend([oldcol_name,newcol_name])
        self.table_counter+=1
        self.renamec+=1
        outname='table{}'.format(self.table_counter)
        return outname

    def addition(self):
        newcol=(self.params['newColumnName']).replace(" ", "_")
        basecol=(self.params['baseColumnName']).replace(" ", "_")
        colInsert=self.params['columnInsertIndex']
        expre=self.params['expression']
        newcol_name='newColumnName:{}'.format(newcol)
        basecol_name='baseColumnName:{}'.format(basecol)
        colInsert_index='columnInsertIndex:{}'.format(colInsert)
        expression='expression:{}'.format(expre)
        # "expression": "grel:cells[\"Sponsor 2\"].value + cells[\"Sponsor 7\"].value"
        # "expression": "grel:value"
        # "expression": "grel:cells.name.value + cells.event.value",   \.\w+\.
        collist=addition_dependency(self.params)
        self.parlist.extend([newcol_name,basecol_name,colInsert_index])
        if len(collist)>1:
            mergecol_name0='mergecolname0:{}'.format(collist[0].replace(" ", "_"))
            mergecol_name1='mergecolname1:{}'.format(collist[1].replace(" ", "_"))
            self.parlist.extend([mergecol_name0,mergecol_name1])
        self.table_counter+=1
        self.addc+=1
        outname='table{}'.format(self.table_counter)
        return outname

    def split(self):
        col=(self.params['columnName']).replace(" ", "_")
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
        col=(self.params['columnName']).replace(" ", "_")
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
            wf[i]['dependency']=wf[i]['columnName'].split()[0]

        elif wf[i]['op']=='core/column-rename':
            if 'dependency' not in wf[i]:
                wf[i]['dependency']=wf[i]['oldColumnName'].split()[0]
            for j in range(i+1,len(wf)):
                if wf[j]['op']=='core/column-addition':
                    #
                    collist=addition_dependency(wf[j])
                    if len(collist)==1:
                        wf[j]['dependency']= wf[j]['newColumnName']
                    # all of the columns in collist should be the dependency
                    wf[j]['dependency']=collist
                elif wf[j]['op']=='core/column-rename':
                    if any([wf[j]['oldColumnName']==wf[i]['newColumnName'],wf[j]['newColumnName']==wf[i]['oldColumnName']]):
                        wf[j]['dependency']=wf[i]['dependency']
                else:
                    if wf[j]['columnName'].split()[0]==wf[i]['newColumnName']:
                        wf[j]['dependency']=wf[i]['dependency']
        elif wf[i]['op']=='core/column-addition':
            collist=addition_dependency(wf[i])
            if 'dependency' not in wf[i]:
                wf[i]['dependency']=collist
            for j in range(i+1,len(wf)):
                if wf[j]['op']=='core/column-addition':
                    subcollist=addition_dependency(wf[j])
                    if len(subcollist)==1:
                        wf[j]['dependency']=wf[j]['newColumnName']
                    wf[j]['dependency']=subcollist
                elif wf[j]['op']=='core/column-rename':
                    if wf[j]['oldColumnName']==wf[i]['newColumnName']:
                        wf[j]['dependency']=wf[i]['newColumnName']
                else:
                    if wf[j]['columnName'].split()[0]==wf[i]['newColumnName']:
                        wf[j]['dependency']=wf[i]['newColumnName']
        elif wf[i]['op']=='core/column-split':
            if 'dependency' not in wf[i]:
                wf[i]['dependency']=wf[i]['columnName'].split()[0]
            for j in range(i+1,len(wf)):
                if wf[j]['op']=='core/column-addition':
                    collist=addition_dependency(wf[j])
                    if len(collist)==1:
                        #  no dependency here
                        wf[j]['dependency']=wf[j]['newColumnName']
                    wf[j]['dependency']=collist
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


def ruleforinput(key_l,value_l,ind,outname,colname):
    # ['A', 'A 1', 'A 2']
    # ['table0', 'A 1',...]
    # {'A': 'table0' , 'A 1': 'table1', 'A 2': '...','' }

    key_l.append(colname)
    #     ['A','A 1']
    value_l.append(outname)
    lenth_list=len(key_l)
    #     ['table0','table1']
    in_name=''
    # linklist={ k.replace(' ', '_'): v for k, v in olinklist.items() }
    if ind==0:
        in_name='table0'
    else:
        # search......' A 1 '
        for idx, name in enumerate(key_l):
            if len(name.split())>1 and colname not in key_l[:lenth_list-1] :  # some condition you like
                # do sth with idx
                value_l[lenth_list-1]=value_l[idx]
                in_name='{}'.format(value_l[lenth_list-1])
                break
            else:
                in_name='{}'.format(outname)
    return in_name


def get_branch_leafs(parents, children):
    children_number = Counter(parents)
    for node in parents:
        if children_number[node] > 1:
            return list(filter(lambda child: children_number[child] == 0, children))
    return [children[-1]]  # no branch


def ruleforoutput(out_l,in_l):
    # in_l:  ['table0', 'col:sponsor1','table1','table2','table3','table3','table4']
    # out_l: ['col:sponsor1','table1','table2','table3','table4', 'table5','table6']
    # duplicate names in in_l:  same input:  branches-> positions
    # make sure the branches are also the dead end -> positions in out_l not shown in in_l
    # using tree to solve this:  Counter: more than one child means branching happen;
    #  find all of the children node from this branch and return it
    branch=get_branch_leafs(in_l,out_l)
    return branch


def writefile(title,description,inputlist,table_counter,yw):
    f=StringIO()
    f.write('#@begin {} #@desc {}\n'.format(title,description))
    for sublist in inputlist:
        f.write('#@param {}\n'.format(sublist))
    f.write('#@in table0\n')
    f.write('#@out table{}\n'.format(table_counter+1))
    # write contents
    key_l=[]
    value_l=[]
    tablec=0
    massedit_c=0
    texttransform_c=0
    split_c=0
    rename_c=0
    add_c=0
    inputl=[]
    outnamelist=[]
    for innerlist in yw:
        ind=0
        outputname='table0'
        col_counter=0
        output=[]
        outputnamelist=[]
        innamelist=[]
        for innerdicts in innerlist:
            wf=WF(innerdicts,inputl,tablec,massedit_c,rename_c,texttransform_c,split_c,add_c,col_counter)
            if innerdicts['op']=='core/column-rename':
                outname=wf.rename()
                ocol_n=innerdicts['oldColumnName']
                ncol_n=innerdicts['newColumnName']
                f.write('#@begin {}{} #@desc {}\n'.format(innerdicts['op'],rename_c,innerdicts['description']))
                f.write('#@param oldColumnName:{}\n'.format(ocol_n.replace(" ", "_")))
                f.write('#@param newColumnName:{}\n'.format(ncol_n.replace(" ", "_")))
                in_name=ruleforinput(key_l,value_l,ind,outputname,ocol_n)
                f.write('#@in {}\n'.format(in_name))
                f.write('#@out {}\n'.format(outname))
                f.write('#@end {}{}\n'.format(innerdicts['op'],rename_c))
                ind+=1
                outputname=outname
                outputnamelist.append(outputname)
                innamelist.append(in_name)
            elif innerdicts['op']=='core/column-addition':
                outname=wf.addition()
                # need further edition
                b_coln=innerdicts['baseColumnName']
                n_coln=innerdicts['columnInsertIndex']
                collist=addition_dependency(innerdicts)
                    # mergecol_name0='mergecolname0:{}'.format(collist[0])
                    # mergecol_name1='mergecolname1:{}'.format(collist[1])

                f.write('#@begin {}{} #@desc {}\n'.format(innerdicts['op'],add_c,innerdicts['description']))
                f.write('#@param baseColumnName:{}\n'.format(b_coln.replace(" ", "_")))
                f.write('#@param columnInsertIndex:{}\n'.format(n_coln))
                f.write('#@param newColumnName:{}\n'.format(innerdicts['newColumnName']))
                if len(collist)>1:
                    mergecol_name0=collist[0].replace(" ", "_")
                    mergecol_name1=collist[1].replace(" ", "_")
                    f.write('#@param mergecolname0:{}\n'.format(mergecol_name0))
                    f.write('#@param mergecolname1:{}\n'.format(mergecol_name1))
                # here need further edition
                in_name=ruleforinput(key_l,value_l,ind,outputname,b_coln)
                f.write('#@in {}\n'.format(in_name))
                f.write('#@out {}\n'.format(outname))
                f.write('#@end {}{}\n'.format(innerdicts['op'],add_c))
                ind+=1
                outputname=outname
                outputnamelist.append(outputname)
                innamelist.append(in_name)
            elif innerdicts['op']=='core/column-split':
                outname=wf.split()
                col_n=innerdicts['columnName']
                f.write('#@begin {}{} #@desc {}\n'.format(innerdicts['op'],split_c,innerdicts['description']))
                f.write('#@param col-name:{}\n'.format(col_n.replace(" ", "_")))
                f.write('#@param removeOriginalColumn:{}\n'.format(innerdicts['removeOriginalColumn']))
                f.write('#@param separator:{}\n'.format(innerdicts['separator']))
                in_name=ruleforinput(key_l,value_l,ind,outputname,col_n)
                f.write('#@in {}\n'.format(in_name))
                f.write('#@out {}\n'.format(outname))
                f.write('#@end {}{}\n'.format(innerdicts['op'],split_c))
                ind+=1
                outputname=outname
                outputnamelist.append(outputname)
                innamelist.append(in_name)
            elif innerdicts['op']=='core/text-transform':
                outname=wf.text_transform()
                col_n=innerdicts['columnName']
                f.write('#@begin {}{} #@desc {}\n'.format(innerdicts['op'],texttransform_c,innerdicts['description']))
                f.write('#@param col-name:{}\n'.format(col_n.replace(" ", "_")))
                f.write('#@param expression:{}\n'.format(innerdicts['expression']))
                in_name=ruleforinput(key_l,value_l,ind,outputname,col_n)
                f.write('#@in {}\n'.format(in_name))
                f.write('#@out {}\n'.format(outname))
                f.write('#@end {}{}\n'.format(innerdicts['op'],texttransform_c))
                ind+=1
                outputname=outname
                outputnamelist.append(outputname)
                innamelist.append(in_name)
            elif innerdicts['op']=='core/mass-edit':
                outname=wf.mass_edit()
                col_n=innerdicts['columnName']
                f.write('#@begin {}{} #@desc {}\n'.format(innerdicts['op'],massedit_c,innerdicts['description']))
                f.write('#@param col-name:{}\n'.format(col_n.replace(" ", "_")))
                in_name=ruleforinput(key_l,value_l,ind,outputname,col_n)
                f.write('#@in {}\n'.format(in_name))
                f.write('#@out {}\n'.format(outname))
                f.write('#@end {}{}\n'.format(innerdicts['op'],massedit_c))
                ind+=1
                outputname=outname
                outputnamelist.append(outputname)
                innamelist.append(in_name)
            col_counter=wf.col_counter
            tablec=wf.table_counter
            massedit_c=wf.mass_editc
            rename_c=wf.renamec
            texttransform_c=wf.texttc
            split_c=wf.splitc
            add_c=wf.addc
        output.extend(ruleforoutput(outputnamelist,innamelist))
        outnamelist.extend(output)
    # merge:
    f.write('#@begin MergeOperationsColumns #@desc Merge the Parallel Column operations\n')
    for out_name in outnamelist:
        f.write('#@in {}\n'.format(out_name))

    f.write('#@out table{}\n'.format(table_counter+1))
    f.write('#@end MergeOperationsColumns\n')

    f.write('#@end {}\n'.format(title))
    output_string=f.getvalue()
    f.close()

    return output_string


class OR2YW:
    def __init__(self):
        """
        Init function for this class, put any initialization attributes that you need here

        """
        pass

    @staticmethod
    def generate_yw_serial(operations,title="Linear_OR",description="Linear OpenRefine Workflow"):
        if title==None:
            title = "Linear_OR"
        if description==None:
            description = "Linear OpenRefine Workflow"
        inputdatalist = []
        data = operations
        outputfinal = 'table' + str(len(data))
        for dicts in data:
            # print('#@begin '+dicts['op']+'#@desc '+dicts['description']+'\n')
            if dicts['op'] == 'core/column-rename':
                # print('#@in '+dicts['oldColumnName']+'\n')
                # print('#@in '+dicts['newColumnName']+'\n')
                oldColumnName = 'oldColumnName:' + dicts['oldColumnName']
                newColumnName = 'newColumnName:' + dicts['newColumnName']
                inputdatalist.append(oldColumnName)
                inputdatalist.append(newColumnName)
            elif dicts['op'] == 'core/mass-edit':
                colname = 'col-name:' + dicts['columnName']
                inputdatalist.append(colname)
            elif dicts['op'] == 'core/text-transform':
                colname = 'col-name:' + dicts['columnName']
                expression = 'expression:' + dicts['expression']
                inputdatalist.append(colname)
                inputdatalist.append(expression)
            elif dicts['op'] == 'core/column-split':
                colname = 'col-name:' + dicts['columnName']
                separator = 'separator:' + '"%s"' % (dicts['separator'])
                remove = 'removeOriginalColumn:%s' % dicts['removeOriginalColumn']
                inputdatalist.append(colname)
                inputdatalist.append(separator)
                inputdatalist.append(remove)

            elif dicts['op']=='core/column-addition':
                colname = 'col-name:' + dicts['baseColumnName']
                newColumnName='newColumnName:{}'.format(dicts['newColumnName'])
                inputdatalist.append(colname)
                inputdatalist.append(newColumnName)


        deinputdatalist = set(inputdatalist)

        # for sublist in list(deinputdatalist):
        #     print('#@in '+sublist)

        # for the subset of the procedure

        # parse and print it out
        #f = open('../yw/Original_LinearParseYW.txt', 'w')
        f = StringIO()
        f.write('#@begin {0} #@desc {1}\n'.format(title,description))
        for sublist in list(deinputdatalist):
            f.write('#@param ' + sublist + '\n')
        f.write('#@in table0\n')
        f.write('#@out ' + outputfinal + '\n')
        rename_c = 0
        massedit_c = 0
        texttrans_c = 0
        colsplit_c = 0
        coladdit_c=0
        table_c = 0
        for dicts in data:
            if dicts['op'] == 'core/column-rename':
                f.write('#@begin core/column-rename%d' % rename_c + '#@desc ' + dicts['description'] + '\n')
                f.write('#@param oldColumnName:' + dicts['oldColumnName'] + '\n')
                f.write('#@param newColumnName:' + dicts['newColumnName'] + '\n')
                f.write('#@in table%d\n' % table_c)
                table_c += 1
                f.write('#@out table%d\n' % table_c)
                f.write('#@end core/column-rename%d\n' % rename_c)

                rename_c += 1

            elif dicts['op'] == 'core/mass-edit':
                f.write('#@begin core/mass-edit%d' % massedit_c + '#@desc ' + dicts['description'] + '\n')
                f.write('#@param col-name:' + dicts['columnName'] + '\n')
                f.write('#@in table%d\n' % table_c)
                table_c += 1
                f.write('#@out table%d\n' % table_c)
                f.write('#@end core/mass-edit%d\n' % massedit_c)
                massedit_c += 1
            elif dicts['op'] == 'core/text-transform':
                f.write('#@begin core/text-transform%d' % texttrans_c + '#@desc ' + dicts['description'] + '\n')
                f.write('#@param col-name:' + dicts['columnName'] + '\n')
                f.write('#@param expression:' + dicts['expression'] + '\n')
                f.write('#@in table%d\n' % table_c)
                table_c += 1
                f.write('#@out table%d\n' % table_c)
                f.write('#@end core/text-transform%d\n' % texttrans_c)
                texttrans_c += 1
            elif dicts['op'] == 'core/column-split':
                f.write('#@begin core/column-split%d' % colsplit_c + '#@desc ' + dicts['description'] + '\n')
                f.write('#@param col-name:' + dicts['columnName'] + '\n')
                f.write('#@param separator:' + '"%s"' % (dicts['separator']) + '\n')
                f.write('#@param removeOriginalColumn:%s\n' % dicts['removeOriginalColumn'])
                f.write('#@in table%d\n' % table_c)
                table_c += 1
                f.write('#@out table%d\n' % table_c)
                f.write('#@end core/column-split%d\n' % colsplit_c)
                colsplit_c += 1
                # {
                #     "op": "core/column-addition",
                #     "description": "Create column Sponsor1 at index 3 based on column Sponsor using expression grel:value",
                #     "engineConfig": {
                #         "mode": "row-based",
                #         "facets": []
                #     },
                #     "newColumnName": "Sponsor1",
                #     "columnInsertIndex": 3,
                #     "baseColumnName": "Sponsor",
                #     "expression": "grel:value",
                #     "onError": "keep-original"
                # },
            elif dicts['op']=='core/column-addition':
                f.write('#@begin core/column-addition%d' % coladdit_c + '#@desc ' + dicts['description'] + '\n')
                f.write('#@param col-name:' + dicts['baseColumnName'] + '\n')
                f.write('#@param newColumnName:' + '"%s"' % (dicts['newColumnName']) + '\n')
                f.write('#@in table%d\n' % table_c)
                table_c += 1
                f.write('#@out table%d\n' % table_c)
                f.write('#@end core/column-addition%d\n' % coladdit_c)
                coladdit_c += 1


        f.write('#@end {}\n'.format(title))
        output_string = f.getvalue()
        f.close()
        return output_string

    @staticmethod
    def generate_yw_parallel(operations,title="Parallel_OR",description="Parallel OpenRefine Workflow"):
        """
        given a list of operations in dictionary format, return yes workflow script in text
        id: list of operations dictionary / json format
        return yw_script (text / string)
        :return:
        """
        if title==None:
            title = "Parallel_OR"
        if description==None:
            description = "Parallel OpenRefine Workflow"

        data=operations
        tablec=0
        inputlist = []
        for datadicts in data:
            inputlist = getInputlist(datadicts, tablec, inputlist)[0]
            tablec = getInputlist(datadicts, tablec, inputlist)[1]
        inputlist = list(set(inputlist))

        # begin name:  params["op"]
        #  columnName,  newColumnName,  baseColumnName, baseColumnName
        # {'column A name': [],   'column B name': []}

        dependencydicts = {}
        dependencydata = add_dependency(data)
        # group them according to the dependency
        for dicts in dependencydata:
            dependencydicts.setdefault(dicts['dependency'], []).append(dicts)

        ywdicts = dependencydicts.values()

        result = writefile(title=title, description=description, inputlist=inputlist,
                             table_counter=tablec, yw=ywdicts)
        #print(result)
        return result

    @staticmethod
    def generate_vg(yw_string,gv_file,java_path=None):
        temp_folder = ""
        tempid = str(uuid.uuid4())
        text_name = "tmp-" + tempid + ".yw"
        #gv_name = "tmp-" + tempid + ".gv"
        with open(temp_folder + text_name, "w") as f:
            f.write(yw_string)
        # look for java
        if java_path!=None:
            if not os.path.isfile(java_path):
                raise BaseException(
                    "Java Binary: {} not found".format(java_path))
        elif FileHelper.is_tool("java"):
            java_path = "java"
        #print(java_path)
        if java_path==None:
            #print("You must have java to run this operation")
            raise BaseException("You must have java to run this operation, or use --java={java_path} to specify java binary")
        print("java found: ",java_path)
        from or2ywtool import OR2YWCore
        path = os.path.dirname(OR2YWCore.__file__)
        #print(path)

        import shutil
        # copy yw.properties to run directory
        shutil.copyfile(path+"/yw.properties","./yw.properties")

        cmd = "cat {} | {} -jar {} graph -c extract.comment='#' > {}".format(temp_folder + text_name, java_path, path+"/yesworkflow-0.2.2.0-SNAPSHOT-jar-with-dependencies.jar", gv_file)
        ps = subprocess.Popen(cmd, shell=True,stderr=subprocess.STDOUT)
        output, error_output = ps.communicate()
        ps.wait()
        os.remove(temp_folder + text_name)
        if error_output != None:
            raise BaseException("you  must have java installed\n"+error_output)
        return gv_file

    @staticmethod
    def generate_dot(yw_string, dot_file, dot_type="png", java_path=None,dot_path=None):
        temp_folder = ""
        tempid = str(uuid.uuid4())
        vg_filename = "{}.vg".format(tempid)
        vg_filename = OR2YW.generate_vg(yw_string,vg_filename,java_path=java_path)
        if dot_path!=None:
            if not os.path.isfile(dot_path):
                raise BaseException(
                    "Dot binary: {} not found".format(dot_path))
        elif FileHelper.is_tool("dot"):
            dot_path = "dot"
        if dot_path==None:
            raise BaseException(
                "You must have dot (graphviz) to run this operation, or use --dot={dot_path} to specify dot binary")
        print("dot found: ",dot_path)
        cmd = "{} -T{} {} -o {}".format(dot_path, dot_type, vg_filename, dot_file)
        ps = subprocess.Popen(cmd, shell=True,stderr=subprocess.STDOUT)
        output, error_output = ps.communicate()
        ps.wait()
        os.remove(vg_filename)
        if error_output != None:
            raise BaseException("you  must have dot (graphviz) installed\n"+error_output)
        return dot_file

class OR2YWFileProcessor():
    def __init__(self):
        pass

    # def generate_yw(self,input_file,type="serial",title=None,description=None):
    def generate_yw(self, input_file, type="serial", **kwargs):
        # read file
        # print(kwargs)
        json_dict = None
        with open(input_file,"r") as file:
            json_dict = json.load(file)
        if type == "serial":
            return OR2YW.generate_yw_serial(json_dict, **kwargs)
        elif type == "parallel":
            return OR2YW.generate_yw_parallel(json_dict, **kwargs)
        else:
            raise BaseException("Workflow type Only Serial or Parallel ")

    def generate_vg_file(self,input_file,output_file,type="serial",java_path=None, **kwargs):
        yw_string = self.generate_yw(input_file=input_file,type=type,**kwargs)
        OR2YW.generate_vg(yw_string,output_file,java_path=java_path)
        return output_file

    def generate_dot_file(self,input_file,output_file,type="serial", dot_type="png", java_path=None, dot_path=None,  **kwargs):
        yw_string = self.generate_yw(input_file=input_file,type=type,**kwargs)
        OR2YW.generate_dot(yw_string,output_file,java_path=java_path, dot_path=dot_path, dot_type=dot_type)
        return output_file

    def generate_yw_file(self,input_file,output_file,type="serial", **kwargs):
        #print(kwargs)
        yw_dict = self.generate_yw(input_file,type,**kwargs)
        with open(output_file,"w") as file:
            file.writelines(yw_dict)
        return output_file


if __name__ == '__main__':
    """
    test vg
    """
    or2ywf = OR2YWFileProcessor()
    or2ywf.generate_vg(input_file="test.json", output_file="test.vg")
