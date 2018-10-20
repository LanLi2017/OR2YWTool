
import json

def checkpath():
    while True:
        try:
            path=raw_input("Enter the input file path: ")
            with open(path,'r')as f:
                f.close()
        except IOError as e:
            print(e)
        else:
            return path

def main():
    inputdatalist=[]

    inputjsonpath=checkpath()
    with open(inputjsonpath,'r')as f:
        data=json.load(f)
        outputfinal='table'+str(len(data))
        for dicts in data:
            # print('#@begin '+dicts['op']+'#@desc '+dicts['description']+'\n')
            if dicts['op']=='core/column-rename':
                # print('#@in '+dicts['oldColumnName']+'\n')
                # print('#@in '+dicts['newColumnName']+'\n')
                oldColumnName='oldColumnName:'+dicts['oldColumnName']
                newColumnName='newColumnName:'+dicts['newColumnName']
                inputdatalist.append(oldColumnName)
                inputdatalist.append(newColumnName)

            elif dicts['op']=='core/mass-edit':
                colname='col-name:'+dicts['columnName']
                inputdatalist.append(colname)
            elif dicts['op']=='core/text-transform':
                colname='col-name:'+dicts['columnName']
                expression='expression:'+dicts['expression']
                inputdatalist.append(colname)
                inputdatalist.append(expression)
            elif dicts['op']=='core/column-split':
                colname='col-name:'+dicts['columnName']
                separator='separator:'+'"%s"'%(dicts['separator'])
                remove='removeOriginalColumn:%s'%dicts['removeOriginalColumn']
                inputdatalist.append(colname)
                inputdatalist.append(separator)
                inputdatalist.append(remove)


    deinputdatalist=set(inputdatalist)

    # for sublist in list(deinputdatalist):
    #     print('#@in '+sublist)

    # for the subset of the procedure

    # parse and print it out
    f=open('../yw/Original_LinearParseYW.txt','w')
    f.write('#@begin LinearOriginalOR#@desc Workflow of Linear original openrefine history\n')
    for sublist in list(deinputdatalist):
        f.write('#@param '+sublist+'\n')
    f.write('#@in table0\n')
    f.write('#@out '+outputfinal+'\n')
    rename_c=0
    massedit_c=0
    texttrans_c=0
    colsplit_c=0
    table_c=0
    for dicts in data:
        if dicts['op']=='core/column-rename':
            f.write('#@begin core/column-rename%d'%rename_c+'#@desc '+dicts['description']+'\n')
            f.write('#@param oldColumnName:'+dicts['oldColumnName']+'\n')
            f.write('#@param newColumnName:'+dicts['newColumnName']+'\n')
            f.write('#@in table%d\n'%table_c)
            table_c+=1
            f.write('#@out table%d\n'%table_c)
            f.write('#@end core/column-rename%d\n'%rename_c)

            rename_c+=1

        elif dicts['op']=='core/mass-edit':
            f.write('#@begin core/mass-edit%d'%massedit_c+'#@desc '+dicts['description']+'\n')
            f.write('#@param col-name:'+dicts['columnName']+'\n')
            f.write('#@in table%d\n'%table_c)
            table_c+=1
            f.write('#@out table%d\n'%table_c)
            f.write('#@end core/mass-edit%d\n'%massedit_c)
            massedit_c+=1
        elif dicts['op']=='core/text-transform':
            f.write('#@begin core/text-transform%d'%texttrans_c+'#@desc '+dicts['description']+'\n')
            f.write('#@param col-name:'+dicts['columnName']+'\n')
            f.write('#@param expression:'+dicts['expression']+'\n')
            f.write('#@in table%d\n'%table_c)
            table_c+=1
            f.write('#@out table%d\n'%table_c)
            f.write('#@end core/text-transform%d\n'%texttrans_c)
            texttrans_c+=1
        elif dicts['op']=='core/column-split':
            f.write('#@begin core/column-split%d'%colsplit_c+'#@desc '+dicts['description']+'\n')
            f.write('#@param col-name:'+dicts['columnName']+'\n')
            f.write('#@param separator:'+'"%s"'%(dicts['separator'])+'\n')
            f.write('#@param removeOriginalColumn:%s\n'%dicts['removeOriginalColumn'])
            f.write('#@in table%d\n'%table_c)
            table_c+=1
            f.write('#@out table%d\n'%table_c)
            f.write('#@end core/column-split%d\n'%colsplit_c)
            colsplit_c+=1


    f.write('#@end LinearOriginalOR\n')
    f.close()

if __name__=='__main__':
    main()
