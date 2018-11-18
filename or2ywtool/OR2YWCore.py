# import all library needed for this class
import json
import re
from collections import Counter

from itertools import groupby
from io import StringIO
import sys
import argparse
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


class YesWorkflowNode:
    def __init__(self, name, desc=''):
        self.name = name
        self.desc = desc
        self.params = []
        self.in_node_names = []
        self.out_node_names = []

        self.raw_operator = None


def merge_basename(operator):
    # two kinds of expressions :
    # 1. the column name has space: "grel:cells[\"Sponsor 2\"].value + cells[\"Sponsor 7\"].value"  : [A-Z]\w+ \d
    # 2. the column name does not have space: "grel:cells.name.value + cells.event.value" :   \.\w+\.
    #  normal one: "grel:value"
    exp=operator['expression']
    res=operator['baseColumnName']
    if exp=='grel:value':
    #      missing information here: if no merge other columns, we still do not know if the new column is set
    # --------dependency as basecolumnName
       result=res
       print('value: {}'.format(result))
       return result
    result=re.findall('\.\w+\.',exp)
    if result:
        newm=[]
        for col in result:
            newm.append(col[1:len(col)-1])
        result=newm
        return result
    else:
        result=re.findall('[A-Z]\w+ \d',exp)
        newm=[]
        for col in result:
            newm.append(col)
        result=newm
        return result


def may_be_split_by(new_column_name, base_column_name):
    new_column_name=new_column_name.replace(" ","_")
    base_column_name=base_column_name.replace(" ","_")
    if len(new_column_name) <= len(base_column_name):
        return False

    base_part = new_column_name[:len(base_column_name)]
    addition_part = new_column_name[len(base_column_name):]
    print(addition_part)
    if base_part != base_column_name:
        return False
    if not re.fullmatch(r'_\d+', addition_part):
        return False

    return True


def translate_operator_json_to_yes_workflow(json_data):
    yes_workflow_data = []

    nodes_num_about_column = Counter()

    def get_column_current_node(column_name):
        column_name=column_name.replace(" ","_")
        if column_name not in nodes_num_about_column:  # guess split
            split_by = None
            for prev_node in reversed(yes_workflow_data):  # newest split
                if prev_node.raw_operator['op'] == 'core/column-split':
                    if may_be_split_by(
                            column_name,
                            prev_node.raw_operator['columnName'],
                    ):
                        split_by = prev_node
                        break
            if split_by is not None:  # possible split found
                node_id = nodes_num_about_column[column_name] = 1
                node_name = column_name + '_' + str(node_id)
                split_by.out_node_names.append(node_name)
                return node_name
            else:
                return create_new_node_of_column(column_name)
        else:
            node_id = nodes_num_about_column[column_name]
            return column_name + '_' + str(node_id)

    def create_new_node_of_column(column_name):
        column_name=column_name.replace(" ","_")
        nodes_num_about_column[column_name] += 1
        return get_column_current_node(column_name)

    for operator in json_data:
        node = YesWorkflowNode(
            name=operator['op'],
            # if no description, 'no description'
            desc=operator.get('description', 'no description'),
        )
        node.raw_operator = operator

        if operator['op'] == 'core/column-addition':  # merge operation
        #     basecol=(self.params['baseColumnName']).replace(" ", "_")
        # colInsert=self.params['columnInsertIndex']
        # newcol=(self.params['newColumnName']).replace(" ", "_")
            node.params+=[
                "baseColumnName:{}".format(operator['baseColumnName'].replace(" ","_")),
                "InsertPosition:{}".format(operator['columnInsertIndex']),
                "newColumnName:{}".format(operator['newColumnName']),
                "GRELexpression:{}".format(operator['expression'])
            ]
            basename=merge_basename(operator)
            if type(basename) is list:
                baseColumnName0=basename[0]
                baseColumnName1= basename[1]
                node.in_node_names += [
                    get_column_current_node(baseColumnName0.replace(" ","_")),
                    get_column_current_node(baseColumnName1.replace(" ","_")),
                ]
            else:
                node.in_node_names += [
                    get_column_current_node(basename.replace(" ","_")),
                ]
            node.out_node_names += [
                create_new_node_of_column(operator['newColumnName'].replace(" ","_")),
            ]

        elif operator['op'] == 'core/column-split':  # split operation
            node.params+=[
                "columnName:{}".format(operator['columnName'].replace(" ","_")),
                "removeOriginalColumn:{}".format(operator['removeOriginalColumn']),
                "separator:{}".format(operator['separator']),
            ]
            node.in_node_names += [
                get_column_current_node(operator['columnName']),
            ]
        elif operator['op'] == 'core/column-rename':  # split operation
            node.params+=[
                "oldColumnName:{}".format(operator['oldColumnName']),
                "newColumnName:{}".format(operator['newColumnName']),
            ]
            node.in_node_names += [
                get_column_current_node(operator['oldColumnName']),
            ]
            node.out_node_names += [
                create_new_node_of_column(operator['newColumnName']),
            ]
        else:  # normal unary operation
            node.params+=[
                "columnName:{}".format(operator['columnName']),
                "expression:{}".format(operator['expression']),
            ]
            node.in_node_names += [
                get_column_current_node(operator['columnName']),
            ]
            node.out_node_names += [
                create_new_node_of_column(operator['columnName']),
            ]

        yes_workflow_data.append(node)

    return yes_workflow_data


def getparams_from_ywdata(yes_workflow_data):
    paramsinputlist=[]
    for node in yes_workflow_data:
        for params_name in node.params:
            paramsinputlist.append(params_name)
    return list(set(paramsinputlist))


def getinput_from_ywdata(yes_workflow_data):
    inputlist=[]
    for node in yes_workflow_data:
        for in_node_name in node.in_node_names:
            inputlist.append(in_node_name)
    return list(set(inputlist))


def getouput_from_ywdata(yes_workflow_data):
    outputlist=[]
    for node in yes_workflow_data:
        for out_node_name in node.out_node_names:
            outputlist.append(out_node_name)
    return list(set(outputlist))


def write_yes_workflow_data_to_file(yes_workflow_data, file):
    counter=0
    for node in yes_workflow_data:
        print('#@begin {}{}'.format(node.name,counter), '#@desc', node.desc, file=file)
        for param in node.params:
            print('#@param', param, file=file)
        for in_node_name in node.in_node_names:
            print('#@in', in_node_name, file=file)
        for out_node_name in node.out_node_names:
            print('#@out', out_node_name, file=file)
        print('#@end {}{}'.format(node.name,counter), file=file)
        counter+=1




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
        yes_workflow_data = translate_operator_json_to_yes_workflow(operations)
        f = StringIO()
        #with open('yes_workflow_script.txt', 'wt', encoding='utf-8') as f:
        print('#@begin {}'.format(title),'#@desc{}'.format(description), file=f)
        inputlist=getinput_from_ywdata(yes_workflow_data)
        paramslist=getparams_from_ywdata(yes_workflow_data)
        for params in paramslist:
            print('#@param {}'.format(params), file=f)
        for input in inputlist:
            print('#@in {}'.format(input),file=f)
        print('#@out {}'.format('CleanData'),file=f)

        # Data Cleaning steps
        write_yes_workflow_data_to_file(yes_workflow_data, f)

        # merge??
        print('#@begin CombineDataCleaningChanges', file=f)
        outputlist=getouput_from_ywdata(yes_workflow_data)
        for output in outputlist:
            print('#@in {}'.format(output), file=f)
        print('#@out {}'.format('CleanData'), file=f)
        print('#@end {}'.format('CombineDataCleaningChanges'),file=f)
        print('#@end {}'.format(title), file=f)
        output_string = f.getvalue()
        f.close()
        return output_string

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
