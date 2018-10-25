from or2ywtool.OR2YWCore import OR2YWFileProcessor
import sys
import argparse;

def run():
    argv = sys.argv
    # required argument
    reqs = ["input","output"]
    parser = argparse.ArgumentParser(description='OR2YW v0.01')
    parser.add_argument('-i','--input',
            help='openrefine json file')
    parser.add_argument('-o', '--output',
                        help='yesworkflow output file')
    parser.add_argument('-t','--type', default="serial",
            help='Workflow Type, Produce [serial,paralel] workflow, Default: serial')
    parser.add_argument('-ot','--outputtype', default="yw",
            help='Output Type, Produce output [yw,gv,png,svg,pdf], Default: yw')
    args = parser.parse_args(argv[1:])
    argobj = vars(args);
    #print(argobj)
    pas_req = True
    for req in reqs:
        if argobj[req]==None:
            pas_req = False
            break

    if pas_req:
        try:
            or2yw_proc = OR2YWFileProcessor()
            or2yw_proc.generate_yw_file(input_file=argobj["input"],output_file=argobj["output"],type=argobj["type"])
            print("File {} generated.".format(argobj["output"]))
        except BaseException as exc:
            print(exc)
    else:
        parser.print_help()

if __name__ == '__main__':
    run()
