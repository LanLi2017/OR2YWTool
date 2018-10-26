# OR2YWTool
Openrefine to Yesworkflow model tool
====================================

The Openrefine to Yesworkflow model(OR2YW) toolkit repository contains or2yw-examples folder,in which uses Ecology_Rodents dataset and NYPL(New York Public Library) Menu dataset as examples.

**[Yesworkflow](https://github.com/yesworkflow-org/yw-prototypes)**.

**[Openrefine](http://openrefine.org/)**.

Overview
--------

This tool aims to provide an auto-parsing method from Openrefine Operation History JSON file to Yesworklfow model. As we know, the openrefine operation history json file works as a data wrangling workflow. However, the structure of the workflow is not transparent enough, where we can not know the dependency and independency of column operations. And through yw model, it classify Openrefine operations into two levels: schema level and column level. 

1.Folder Structure
------------------
Take Ecology_rodents folder as an example:

folder        |  Function
--------------|------------
dataset       |  "messy dataset"
facts         |  "File for storing prolog facts about scripts"
gv            |  Save the DOT output to a file
pdf           |  Render gv file as PDF file using Graphviz's dot command
png           |  Render gv file as PNG file using Graphviz's dot command
results       |  Screenshot the models
script        |  Auto-parsing file: Linear/Serial-Parallell and the Openrefine json file
yw            |  The parsed yw comments
yw.properties |  yw settings for graph(yw) command
yw_generate.sh|  cheatsheet command

2.Toolkit Usage
----------------
1. Python Version : 3+
a. Install the or2yw package from pip install: 
     
       $ pip  install upgrade --index-url https://test.pypi.org/simple/ or2ywtool

(Note: double check the pip version, if pip is for version 2, then use pip3 install...)

2. After successfully install the or2yw tool, use commands for generating YW file:

       $ or2yw --help
        OR2YW v0.01

          optional arguments:
            -h, --help            show this help message and exit
            -i INPUT, --input INPUT
                                  openrefine json file
            -o OUTPUT, --output OUTPUT
                                  yesworkflow output file
            -t TYPE, --type TYPE  Workflow Type, Produce [serial,paralel] workflow,
                                  Default: serial
            -ot OUTPUTTYPE, --outputtype OUTPUTTYPE
                                  Output Type, Produce output [yw,gv,png,svg,pdf],
                                  Default: yw
        
   a. Generate Serial yw file:
      
       $ or2yw -i test.json -o test.yw -t 
   
   b. Generate Parallel yw file:
       
       $ or2yw -i test.json -o test.yw -t parallel
   

  


