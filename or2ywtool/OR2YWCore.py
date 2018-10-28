# import all library needed for this class
import json

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


def writefile(title,description,inputlist,table_counter,yw):
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


class OR2YW:
    def __init__(self):
        """
        Init function for this class, put any initialization attributes that you need here

        """
        pass

    @staticmethod
    def generate_yw_serial(operations,title="Linear_OR",description="Linear OpenRefine Workflow"):
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
        print(result)
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
        print(java_path)
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
            raise BaseException("you  must have java installed")
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
        print(dot_path)
        cmd = "{} -T{} {} -o {}".format(dot_path, dot_type, vg_filename, dot_file)
        ps = subprocess.Popen(cmd, shell=True,stderr=subprocess.STDOUT)
        output, error_output = ps.communicate()
        ps.wait()
        os.remove(vg_filename)
        if error_output != None:
            raise BaseException("you  must have dot (graphviz) installed")
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