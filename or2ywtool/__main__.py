from or2ywtool.OR2YWCore import OR2YWFileProcessor
import sys
import argparse;

def run():
    argv = sys.argv
    # required argument
    reqs = ["input","output"]
    parser = argparse.ArgumentParser(description='OR2YW v0.0.1')
    parser.add_argument('-i','--input',
            help='openrefine json file')
    parser.add_argument('-o', '--output',
                        help='yesworkflow output file')
    parser.add_argument('-t','--type', default="serial",
            help='Workflow Type, Produce [serial,parallel,merge] workflow, Default: serial')
    parser.add_argument('-ot','--outputtype', default="yw",
            help='Output Type, Produce output [yw,gv,png,svg,pdf], Default: yw')
    parser.add_argument('-java','--java',default=None,help="Java Path, if not initialized will use the java installation environment path")
    parser.add_argument('-dot','--dot',default=None,help="Dot Path, if not initialized will use the dot installation environment path")
    parser.add_argument('-title','--title', default=None,
            help='Title for the Workflow')
    parser.add_argument('-desc','--description', default=None,
            help='Description for the Workflow')
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
            if argobj["outputtype"] == "yw":
                or2yw_proc.generate_yw_file(input_file=argobj["input"],output_file=argobj["output"],type=argobj["type"],title=argobj["title"],description=argobj["description"])
            elif argobj["outputtype"] == "gv":
                or2yw_proc.generate_vg_file(input_file=argobj["input"], output_file=argobj["output"],
                                            type=argobj["type"], title=argobj["title"],
                                            description=argobj["description"],java_path=argobj["java"])
            elif argobj["outputtype"] in ["png","svg","pdf"]:
                or2yw_proc.generate_dot_file(input_file=argobj["input"], output_file=argobj["output"], dot_type=argobj["outputtype"],
                                            type=argobj["type"], title=argobj["title"],
                                            description=argobj["description"],java_path=argobj["java"],dot_path=argobj["dot"])
            else:
                raise BaseException("output type not recognized: {}".format(argobj["outputtype"]))
            print("File {} generated.".format(argobj["output"]))
        except BaseException as exc:
            import traceback
            parser.print_help()
            traceback.print_exc()
    else:
        parser.print_help()

if __name__ == '__main__':
    run()
