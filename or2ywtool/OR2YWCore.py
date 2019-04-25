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
import networkx as nx


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
    exp = operator['expression']
    res = operator['baseColumnName']
    if exp == 'grel:value':
        #      missing information here: if no merge other columns, we still do not know if the new column is set
        # --------dependency as basecolumnName
        result = res
        print('value: {}'.format(result))
        return result
    result = re.findall('\.\w+\.', exp)
    if result:
        newm = []
        for col in result:
            newm.append(col[1:len(col) - 1])
        result = newm
        return result
    else:
        result = re.findall('[A-Z]\w+ \d', exp)
        newm = []
        for col in result:
            newm.append(col)
        result = newm
        return result


def may_be_split_by(new_column_name, base_column_name):
    new_column_name = new_column_name.replace(" ", "_")
    base_column_name = base_column_name.replace(" ", "_")
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

    # variable for storing process graph
    process_graph = {}
    column_all = []

    nodes_num_about_column = Counter()

    def get_column_current_node(column_name):
        column_name = column_name.replace(" ", "_")
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
            if node_id-1 == 0:
                # this is for every first node
                return column_name
            else:
                return column_name + '_' + str(node_id-1)

    def create_new_node_of_column(column_name):
        column_name = column_name.replace(" ", "_")
        nodes_num_about_column[column_name] += 1
        return get_column_current_node(column_name)

    refine_output = []
    refine_subs = []

    for operator in json_data:
        node = YesWorkflowNode(
            name=operator['op'],
            # if no description, 'no description'
            desc=operator.get('description', 'no description').replace('"', '\\"'),
        )
        node.raw_operator = operator

        # initialize column_name with empty string
        column_name = ""
        process_name = ""
        input_columns = []
        output_columns = []

        # nikolaus: parameter input column_name is not really useful in the workflow and can make confusion,
        # I remark any in_node_names that have input column name parameter

        if operator['op'] == 'core/column-addition':  # merge operation
            #     basecol=(self.params['baseColumnName']).replace(" ", "_")
            # colInsert=self.params['columnInsertIndex']
            # newcol=(self.params['newColumnName']).replace(" ", "_")
            node.params += [
                "baseColumnName:{}".format(operator['baseColumnName'].replace(" ", "_")),
                "InsertPosition:{}".format(operator['columnInsertIndex']),
                "newColumnName:{}".format(operator['newColumnName']),
                "GRELexpression:{}".format(operator['expression'])
            ]
            basename = merge_basename(operator)
            # trap for basename
            if len(basename) != 2:
                continue
            if type(basename) is list:
                baseColumnName0 = basename[0]
                baseColumnName1 = basename[1]
                node.in_node_names += [
                    get_column_current_node(baseColumnName0.replace(" ", "_")),
                    get_column_current_node(baseColumnName1.replace(" ", "_")),
                ]
            else:
                node.in_node_names += [
                    get_column_current_node(basename.replace(" ", "_")),
                ]
            node.out_node_names += [
                create_new_node_of_column(operator['newColumnName'].replace(" ", "_")),
            ]

            # assign column_name
            column_name = operator['baseColumnName']
            output_columns.append(operator["newColumnName"])
        elif operator['op'] == 'core/column-split':  # split operation
            node.params += [
                #"columnName:{}".format(operator['columnName'].replace(" ", "_")),
                "removeOriginalColumn:{}".format(operator['removeOriginalColumn']),
                "separator:{}".format(operator['separator']),
            ]
            node.in_node_names += [
                get_column_current_node(operator['columnName']),
            ]
            node.out_node_names += [
                create_new_node_of_column(operator['columnName']),
            ]
            # assign column_name
            column_name = operator['columnName']
        elif operator['op'] == 'core/column-rename':  # split operation
            node.params += [
                "oldColumnName:{}".format(operator['oldColumnName']),
                "newColumnName:{}".format(operator['newColumnName']),
            ]
            node.in_node_names += [
                get_column_current_node(operator['oldColumnName']),
            ]
            node.out_node_names += [
                create_new_node_of_column(operator['newColumnName']),
            ]
            # assign column_name
            column_name = operator['oldColumnName']
            output_columns.append(operator["newColumnName"])
        elif operator['op'] == 'core/column-removal':
            node.in_node_names+=[
                get_column_current_node(operator['columnName']),
            ]
            node.out_node_names+=[
                create_new_node_of_column('remove-{}'.format(operator['columnName']))
            ]
            column_name=operator['columnName']
        elif operator['op']=='core/column-addition-by-fetching-urls':
            node.params+=[
                "newColumnName:{}".format(operator['newColumnName']),
                "columnInsertIndex:{}".format(operator['columnInsertIndex']),
                "baseColumnName:{}".format(operator['baseColumnName']),
                "urlExpression:{}".format(operator['urlExpression']),
            ]
            node.in_node_names+=[
                get_column_current_node(operator['baseColumnName'])
            ]
            node.out_node_names+=[
                create_new_node_of_column(operator['newColumnName'])
            ]
            column_name=operator['baseColumnName']
            output_columns.append(operator['newColumnName'])
        elif operator['op']=='core/multivalued-cell-join':
            node.params+=[
                "keyColumnName:{}".format(operator['keyColumnName']),
                "separator:{}".format(operator['separator']),
            ]
            node.in_node_names+=[
                get_column_current_node(operator['columnName'])
            ]
            node.out_node_names+=[
                create_new_node_of_column(operator['columnName'])
            ]
            column_name=operator['columnName']
        elif operator['op']=='core/transpose-columns-into-rows':
            node.params+=[
                "startColumnName:{}".format(operator['startColumnName']),
                "columnCount:{}".format(operator['columnCount']),
                "ignoreBlankCells:{}".format(operator['ignoreBlankCells']),
                "combinedColumnName:{}".format(operator['combinedColumnName']),
                "separator:{}".format(operator['separator']),
            ]
            node.in_node_names+=[
                get_column_current_node(operator['startColumnName'])
            ]
            node.out_node_names+=[
                create_new_node_of_column(operator['combinedColumnName'])
            ]
            column_name=operator['startColumnName']
            output_columns.append(operator['combinedColumnName'])
        elif operator['op']=='core/row-removal':
            node.params+=[
                "mode:{}".format(operator['engineConfig']['mode'])
            ]
            node.in_node_names+=[
                get_column_current_node(operator['engineConfig']['facets'][0]['name'])
            ]
            node.out_node_names+=[
                create_new_node_of_column(operator['engineConfig']['facets'][0]['name'])
            ]
            column_name=operator['engineConfig']['facets'][0]['name']
        elif operator['op']=='core/column-move':
            node.params+=[
                "index:{}".format(operator['index'])
            ]
            node.in_node_names+=[
                get_column_current_node(operator['columnName'])
            ]
            node.out_node_names+=[
                create_new_node_of_column(operator['columnName'])
            ]
            column_name=operator['columnName']

        else:  # normal unary operation
            # print("op: ",operator.items())
            # if operator["op"].startswith("group"):
            #    print(operator["op"])
            try:
                node.params += [
                    #"columnName:{}".format(operator['columnName']),
                    "expression:{}".format(operator['expression']),
                ]
                node.in_node_names += [
                    get_column_current_node(operator['columnName']),
                ]
                node.out_node_names += [
                    create_new_node_of_column(operator['columnName']),
                ]
                # assign column_name
                column_name = operator['columnName']
            except KeyError:
                continue

        # rewrite the params, replace space with _ to avoid unexpected cut values
        for i, x in enumerate(node.params):
            node.params[i] = x.replace(" ", "_")

        # check column_name and retrace the graph
        if column_name != "":
            # check if it's already recorded previouly
            if column_name not in column_all:
                column_all.append(column_name)
                # check if it's result from the split column operation
                temp_col_arr = column_name.split(" ")
                # print(temp_col_arr)
                if len(temp_col_arr) > 1:
                    # check if the last index is a numeric
                    # is_num = False
                    try:
                        # assert convert to int
                        assert int(temp_col_arr[-1]) > 0
                        # is_num=True
                        source_column = " ".join(temp_col_arr[0:-1])
                        # print(source_column)
                        # print(column_all)
                        if source_column in column_all:
                            # trace process in the source column
                            # to get split operation
                            # print("in all")
                            for p_temp in process_graph[source_column]:
                                # print(p_temp)
                                if p_temp["op"] == "core/column-split":
                                    # input_columns.append("{}-p{}".format(source_column,p_temp["index"]))
                                    input_columns.append("{}-p{}".format(source_column, p_temp["index"]))
                            # print(input_columns)
                    except:
                        pass

            # check if the colunn_name in the node
            if column_name not in process_graph.keys():
                # add new _node
                process_graph[column_name] = []
            process_graph[column_name].append(
                {"index": len(process_graph[column_name]) + 1, "op": operator["op"], "all_op": operator,
                 "input": input_columns, "output": output_columns})

        yes_workflow_data.append(node)

    # recreate graph
    p_graph = nx.DiGraph()
    temp_output_edges = []

    # create a subgraph to store repetitive process
    sub_graph = []

    # print(process_graph)

    for col_key, col_item in process_graph.items():
        p_graph.add_node(col_key, attr={"op": "input_column", "index": 0})
        source_node = col_key
        temp_process = None

        sub_graph = []
        duplicates = False
        for i, process in enumerate(col_item):
            # print(i)
            # merge repetitive operations
            # print(process["op"])
            if len(process["output"]) == 0 and len(process["input"]) == 0:
                if i < len(col_item) - 1:
                    if process["op"] == col_item[i + 1]["op"]:
                        # print("dupl")
                        duplicates = True
                        sub_graph.append(process["all_op"].copy())
                        continue
                # else:
                # if temp_process == None:
                #    first_time = False
                temp_process = process["op"]
                # create a simplify output
                sub_graph.append(process["all_op"].copy())
                refine_output.append(process["all_op"].copy())
            # print("len sub",len(sub_graph))

            # if len(sub_graph)>1:
            if duplicates:
                # print("sub_graph_{}".format(len(refine_subs)))
                # print(refine_output[len(refine_output)-1]["op"])
                refine_output[len(refine_output) - 1][
                    "description"] = "group of {} with {} operations, details in sub_ops_{}.json".format(
                    refine_output[len(refine_output) - 1]["op"], len(sub_graph), len(refine_subs) + 1)
                refine_output[len(refine_output) - 1]["op"] = "group_{1}_{0}".format(
                    refine_output[len(refine_output) - 1]["op"], len(refine_subs) + 1)
                refine_output[len(refine_output) - 1]["expression"] = "sub_ops_{}".format(len(refine_subs) + 1)
                # print(refine_output[len(refine_output)-1]["all_op"]["op"])
                refine_subs.append(sub_graph)

                sub_graph = []
                duplicates = False
            else:
                # if not duplicates
                process_node = "{}-p{}".format(col_key, i + 1)
                p_graph.add_node(process_node, attr=process, op=process["op"])
                p_graph.add_edge(source_node, process_node)
                # print(source_node,process_node)

                for output in process["output"]:
                    temp_output_edges.append((process_node, output))
                for t_input in process["input"]:
                    # temp_input_edges.append(t_input,process_node)
                    # print(t_input)
                    temp_output_edges.append((t_input, process_node))
                source_node = process_node

    # recreate output connection
    for output_edge in temp_output_edges:
        # print(output_edge)
        p_graph.add_edge(output_edge[0], output_edge[1])

    # merge repetitive operations
    # for col_key

    return yes_workflow_data, p_graph, refine_output, refine_subs, nodes_num_about_column


def getparams_from_ywdata(yes_workflow_data):
    paramsinputlist = []
    for node in yes_workflow_data:
        for params_name in node.params:
            paramsinputlist.append(params_name)
    return list(set(paramsinputlist))


def getinput_from_ywdata(yes_workflow_data):
    inputlist = []
    for node in yes_workflow_data:
        for in_node_name in node.in_node_names:
            inputlist.append(in_node_name)
    return list(set(inputlist))


def getouput_from_ywdata(yes_workflow_data):
    outputlist = []
    #for node in yes_workflow_data:
    #    for out_node_name in node.out_node_names:
    #        outputlist.append(out_node_name)

    return list(set(outputlist))


def write_yes_workflow_data_to_file(yes_workflow_data, file):
    counter = 0
    for node in yes_workflow_data:
        #print(node.in_node_names,node.out_node_names,node.name)
        print('#@begin {}{}'.format(node.name, counter), '#@desc', node.desc, file=file)
        for param in node.params:
            print('#@param', param, file=file)
        for in_node_name in node.in_node_names:
            print('#@in', in_node_name, file=file)
        for out_node_name in node.out_node_names:
            print('#@out', out_node_name, file=file)
        print('#@end {}{}'.format(node.name, counter), file=file)
        counter += 1


class OR2YW:
    def __init__(self):
        """
        Init function for this class, put any initialization attributes that you need here

        """
        pass

    @staticmethod
    def generate_yw_serial(operations, title="Linear_OR", description="Linear OpenRefine Workflow"):
        if title == None:
            title = "Linear_OR"
        if description == None:
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

            elif dicts['op'] == 'core/column-addition':
                colname = 'col-name:' + dicts['baseColumnName']
                newColumnName = 'newColumnName:{}'.format(dicts['newColumnName'])
                inputdatalist.append(colname)
                inputdatalist.append(newColumnName)

            elif dicts['op']=='core/column-removal':
                colname='col-name:{}'.format(dicts['columnName'])
                inputdatalist.append(colname)

            elif dicts['op']=='core/row-removal':
                colname='col-name:'+dicts['engineConfig']['facets'][0]['columnName']
                expression='expression:"%s"'%(dicts['engineConfig']['facets'][0]['expression'])
                inputdatalist.append(colname)
                inputdatalist.append(expression)


            elif dicts['op']=='core/row-flag':
                flagged='flagged:"%s"'%dicts['flagged']
                inputdatalist.append(flagged)

            elif dicts['op']=='core/column-addition-by-fetching-urls':
                colname='col-name:'+dicts['baseColumnName']
                newColumnName='newColumnName:{}'.format(dicts['newColumnName'])
                urlExpression='urlExpression:{}'.format(dicts['urlExpression'])
                inputdatalist.append(colname)
                inputdatalist.append(newColumnName)
                inputdatalist.append(urlExpression)

            elif dicts['op']=='core/column-move':
                colname='col-name:{}'.format(dicts['columnName'])
                index='index:{}'.format(dicts['index'])
                inputdatalist.append(colname)
                inputdatalist.append(index)
            elif dicts['op']=='core/multivalued-cell-join':
                colname='col-name:{}'.format(dicts['columnName'])
                keyColumnName='keyColumnName:{}'.format(dicts['keyColumnName'])
                separator='separator:{}'.format(dicts['separator'])
                inputdatalist.append(colname)
                inputdatalist.append(keyColumnName)
                inputdatalist.append(separator)
            elif dicts['op']=='core/transpose-columns-into-rows':
                colname='col-name:{}'.format(dicts['startColumnName'])
                columnCount='columnCount:{}'.format(dicts['columnCount'])
                combinedColumnName='combinedColumnName:{}'.format(dicts['combinedColumnName'])
                separator='separator:{}'.format(dicts['separator'])
                inputdatalist.append(colname)
                inputdatalist.append(columnCount)
                inputdatalist.append(combinedColumnName)
                inputdatalist.append(separator)




        deinputdatalist = set(inputdatalist)

        # for sublist in list(deinputdatalist):
        #     print('#@in '+sublist)

        # for the subset of the procedure

        # parse and print it out
        # f = open('../yw/Original_LinearParseYW.txt', 'w')
        f = StringIO()
        f.write('#@begin {0} #@desc {1}\n'.format(title, description))
        for sublist in list(deinputdatalist):
            f.write('#@param ' + sublist + '\n')
        f.write('#@in table0\n')
        f.write('#@out ' + outputfinal + '\n')
        rename_c = 0
        massedit_c = 0
        texttrans_c = 0
        colsplit_c = 0
        coladdit_c = 0
        coladd_url_c=0
        colremov_c=0
        colmove_c=0
        rowremov_c=0
        table_c = 0
        flag_c=0
        multi_value_join_c=0
        trans_col2rows_c=0
        for dicts in data:
            dicts['description'] = dicts['description'].replace('"', '\\"')
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
            elif dicts['op'] == 'core/column-addition':
                f.write('#@begin core/column-addition%d' % coladdit_c + '#@desc ' + dicts['description'] + '\n')
                f.write('#@param col-name:' + dicts['baseColumnName'] + '\n')
                f.write('#@param newColumnName:' + '"%s"' % (dicts['newColumnName']) + '\n')
                f.write('#@in table%d\n' % table_c)
                table_c += 1
                f.write('#@out table%d\n' % table_c)
                f.write('#@end core/column-addition%d\n' % coladdit_c)
                coladdit_c += 1
            elif dicts['op']=='core/column-removal':
                f.write('#@begin core/column-removal%d' % colremov_c + '#@desc ' + dicts['description'] + '\n')
                f.write('#@param col-name:' + dicts['columnName'] + '\n')
                f.write('#@in table%d\n' % table_c)
                table_c += 1
                f.write('#@out table%d\n' % table_c)
                f.write('#@end core/column-removal%d\n' % colremov_c)
                colremov_c += 1

            elif dicts['op']=='core/row-removal':
                f.write('#@begin core/row-removal%d' % rowremov_c + '#@desc ' + dicts['description'] + '\n')
                f.write('#@param col-name:' + dicts['engineConfig']['facets'][0]['columnName'] + '\n')
                f.write('#@param expression:' + '"%s"' % (dicts['engineConfig']['facets'][0]['expression']) + '\n')
                f.write('#@in table%d\n' % table_c)
                table_c += 1
                f.write('#@out table%d\n' % table_c)
                f.write('#@end core/row-removal%d\n' % rowremov_c)
                rowremov_c += 1
            elif dicts['op']=='core/row-flag':
                f.write('#@begin core/row-flag%d' % flag_c + '#@desc ' + dicts['description'] + '\n')
                f.write('#@param flagged:' + '"%s"' % dicts['flagged'] + '\n')
                f.write('#@in table%d\n' % table_c)
                table_c += 1
                f.write('#@out table%d\n' % table_c)
                f.write('#@end core/row-flag%d\n' % flag_c)
                flag_c += 1

            elif dicts['op']=='core/column-addition-by-fetching-urls':
                f.write('#@begin core/column-addition-by-fetching-urls%d' % coladd_url_c + '#@desc ' + dicts['description'] + '\n')
                f.write('#@param col-name:{}'.format(dicts['baseColumnName'])+ '\n')
                f.write('#@param newColumnName:{}'.format(dicts['newColumnName'])+ '\n')
                f.write('#@param urlExpression:{}'.format(dicts['urlExpression'])+'\n')
                f.write('#@in table%d\n' % table_c)
                table_c += 1
                f.write('#@out table%d\n' % table_c)
                f.write('#@end core/column-addition-by-fetching-urls%d\n' % coladd_url_c)
                coladd_url_c += 1

            elif dicts['op']=='core/column-move':
                f.write('#@begin core/column-move%d' %colmove_c + '#@desc '+ dicts['description']+'\n')
                f.write('#@param col-name:{}'.format(dicts['columnName'])+ '\n')
                f.write('#@param index:{}'.format(dicts['index'])+ '\n')
                f.write('#@in table%d\n' % table_c)
                table_c += 1
                f.write('#@out table%d\n' % table_c)
                f.write('#@end core/column-move%d\n' %colmove_c)
                colmove_c+=1

            elif dicts['op']=='core/multivalued-cell-join':
                f.write('#@begin core/multivalued-cell-join%d' % multi_value_join_c + '#@desc ' + dicts['description'] + '\n')
                f.write('#@param col-name:' + dicts['columnName'] + '\n')
                f.write('#@param keyColumnName:' + dicts['keyColumnName'] + '\n')
                f.write('#@param separator:'+dicts['separator']+'\n')
                f.write('#@in table%d\n' % table_c)
                table_c += 1
                f.write('#@out table%d\n' % table_c)
                f.write('#@end core/multivalued-cell-join%d\n' % multi_value_join_c)
                multi_value_join_c += 1

            elif dicts['op']=='core/transpose-columns-into-rows':
                f.write('#@begin core/transpose-columns-into-rows%d' % trans_col2rows_c + '#@desc ' + dicts['description'] + '\n')
                f.write('#@param col-name:' + dicts['startColumnName'] + '\n')
                f.write('#@param columnCount:%d'%dicts['columnCount'] + '\n')
                f.write('#@param combinedColumnName:'+dicts['combinedColumnName']+'\n')
                f.write('#@param separator:'+dicts['separator']+'\n')
                f.write('#@in table%d\n' % table_c)
                table_c += 1
                f.write('#@out table%d\n' % table_c)
                f.write('#@end core/transpose-columns-into-rows%d\n' % trans_col2rows_c)
                trans_col2rows_c += 1



        f.write('#@end {}\n'.format(title))
        output_string = f.getvalue()
        f.close()

        # clear space chars in param, in, and out notation
        output_list = output_string.split("\n")
        for i,x in enumerate(output_list):
            if x.startswith("#@param"):
                print(x)
                output_list[i] = "#@param " + x[8:].replace(" ","_")
            elif x.startswith("#@in"):
                output_list[i] = "#@in " + x[5:].replace(" ", "_")
            elif x.startswith("#@out"):
                output_list[i] = "#@out " + x[6:].replace(" ", "_")

        output_string = "\n".join(output_list)

        # output_string = output_string.replace('"','\\"')
        return output_string

    @staticmethod
    def generate_yw_parallel(operations, title="Parallel_OR", description="Parallel OpenRefine Workflow", merge=False):
        """
        given a list of operations in dictionary format, return yes workflow script in text
        id: list of operations dictionary / json format
        return yw_script (text / string)
        :return:
        """
        if title == None:
            title = "Parallel_OR"
        if description == None:
            description = "Parallel OpenRefine Workflow"
        #yes_workflow_data = translate_operator_json_to_yes_workflow(operations)
        yes_workflow_data, p_graph, refine_output, refine_subs, nodes_num = translate_operator_json_to_yes_workflow(operations)

        #print(yes_workflow_data)

        if merge:
            yes_workflow_data, _, _, _, nodes_num = translate_operator_json_to_yes_workflow(refine_output)
            for i, sub in enumerate(refine_subs):
                with open("sub_ops_{}.json".format(i + 1), "w") as file:
                    json.dump(sub, file)

        f = StringIO()
        # with open('yes_workflow_script.txt', 'wt', encoding='utf-8') as f:
        print('#@begin {}'.format(title), '#@desc {}'.format(description), file=f)
        inputlist = getinput_from_ywdata(yes_workflow_data)
        paramslist = getparams_from_ywdata(yes_workflow_data)
        for params in paramslist:
            print('#@param {}'.format(params.replace(" ","_")), file=f)
        for input in inputlist:
            print('#@in {}'.format(input.replace(" ","_")), file=f)
        print('#@out {}'.format('CleanData'), file=f)

        # Data Cleaning steps
        write_yes_workflow_data_to_file(yes_workflow_data, f)

        # merge??
        print('#@begin CombineDataCleaningChanges', file=f)
        # change the output list to make no confusion
        #outputlist = getouput_from_ywdata(yes_workflow_data)
        #for output in outputlist:
        #    print('#@in {}'.format(output.replace(" ","_")), file=f)

        for key in nodes_num:
            if nodes_num[key]-1 == 0:
                text = "{}".format(key)
            else:
                text = str(key)+"_"+str(nodes_num[key]-1)
            #print(text)
            print('#@in {}'.format(text), file=f)

        print('#@out {}'.format('CleanData'), file=f)
        print('#@end {}'.format('CombineDataCleaningChanges'), file=f)
        print('#@end {}'.format(title), file=f)
        output_string = f.getvalue()
        f.close()
        return output_string

    @staticmethod
    def generate_vg(yw_string, gv_file, java_path=None):
        temp_folder = ""
        tempid = str(uuid.uuid4())
        text_name = "tmp-" + tempid + ".yw"
        # gv_name = "tmp-" + tempid + ".gv"
        with open(temp_folder + text_name, "w") as f:
            f.write(yw_string)
        # look for java
        if java_path != None:
            if not os.path.isfile(java_path):
                raise BaseException(
                    "Java Binary: {} not found".format(java_path))
        elif FileHelper.is_tool("java"):
            java_path = "java"
        # print(java_path)
        if java_path == None:
            # print("You must have java to run this operation")
            raise BaseException(
                "You must have java to run this operation, or use --java={java_path} to specify java binary")
        print("java found: ", java_path)
        from or2ywtool import OR2YWCore
        path = os.path.dirname(OR2YWCore.__file__)
        # print(path)

        import shutil
        # copy yw.properties to run directory
        shutil.copyfile(path + "/yw.properties", "./yw.properties")

        cmd = "cat {} | {} -jar {} graph -c extract.comment='#' > {}".format(temp_folder + text_name, java_path,
                                                                             path + "/yesworkflow-0.2.2.0-SNAPSHOT-jar-with-dependencies.jar",
                                                                             gv_file)
        ps = subprocess.Popen(cmd, shell=True, stderr=subprocess.STDOUT)
        output, error_output = ps.communicate()
        ps.wait()
        os.remove(temp_folder + text_name)
        if error_output != None:
            raise BaseException("you  must have java installed\n" + error_output)
        return gv_file

    @staticmethod
    def generate_dot(yw_string, dot_file, dot_type="png", java_path=None, dot_path=None):
        temp_folder = ""
        tempid = str(uuid.uuid4())
        vg_filename = "{}.vg".format(tempid)
        vg_filename = OR2YW.generate_vg(yw_string, vg_filename, java_path=java_path)
        if dot_path != None:
            if not os.path.isfile(dot_path):
                raise BaseException(
                    "Dot binary: {} not found".format(dot_path))
        elif FileHelper.is_tool("dot"):
            dot_path = "dot"
        if dot_path == None:
            raise BaseException(
                "You must have dot (graphviz) to run this operation, or use --dot={dot_path} to specify dot binary")
        print("dot found: ", dot_path)
        cmd = "{} -T{} {} -o {}".format(dot_path, dot_type, vg_filename, dot_file)
        ps = subprocess.Popen(cmd, shell=True, stderr=subprocess.STDOUT)
        output, error_output = ps.communicate()
        ps.wait()
        os.remove(vg_filename)
        if error_output != None:
            raise BaseException("you  must have dot (graphviz) installed\n" + error_output)
        return dot_file


class OR2YWFileProcessor():
    def __init__(self):
        pass

    # def generate_yw(self,input_file,type="serial",title=None,description=None):
    def generate_yw(self, input_file, type="serial", **kwargs):
        # read file
        # print(kwargs)
        json_dict = None
        with open(input_file, "r") as file:
            json_dict = json.load(file)
        if type == "serial":
            return OR2YW.generate_yw_serial(json_dict, **kwargs)
        elif type == "parallel":
            return OR2YW.generate_yw_parallel(json_dict, **kwargs)
        elif type == "merge":
            return OR2YW.generate_yw_parallel(json_dict, merge=True, **kwargs)
        else:
            raise BaseException("Workflow type Only Serial, Parallel or Merge")

    def generate_vg_file(self, input_file, output_file, type="serial", java_path=None, **kwargs):
        yw_string = self.generate_yw(input_file=input_file, type=type, **kwargs)
        OR2YW.generate_vg(yw_string, output_file, java_path=java_path)
        return output_file

    def generate_dot_file(self, input_file, output_file, type="serial", dot_type="png", java_path=None, dot_path=None,
                          **kwargs):
        yw_string = self.generate_yw(input_file=input_file, type=type, **kwargs)
        OR2YW.generate_dot(yw_string, output_file, java_path=java_path, dot_path=dot_path, dot_type=dot_type)
        return output_file

    def generate_yw_file(self, input_file, output_file, type="serial", **kwargs):
        # print(kwargs)
        yw_dict = self.generate_yw(input_file, type, **kwargs)
        with open(output_file, "w") as file:
            file.writelines(yw_dict)
        return output_file


if __name__ == '__main__':
    """
    test vg
    """
    or2ywfile=OR2YWFileProcessor().generate_yw_file('../graph_analysis/test.json','test.yw')
    # or2ywf = OR2YWFileProcessor()
    # or2ywf.generate_vg(input_file="test.json", output_file="test.vg")
