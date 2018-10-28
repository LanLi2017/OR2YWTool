# OR2YWTool
Openrefine to Yesworkflow model tool
====================================

The Openrefine to Yesworkflow model(OR2YW) toolkit repository contains or2yw-examples folder,in which uses Ecology_Rodents dataset and NYPL(New York Public Library) Menu dataset as examples.

**[Yesworkflow](https://github.com/yesworkflow-org/yw-prototypes)**.

**[Openrefine](http://openrefine.org/)**.

Overview
--------

This tool aims to provide an auto-parsing method from Openrefine Operation History JSON file to Yesworklfow model. As we know, the openrefine operation history json file works as a data wrangling workflow. However, the structure of the workflow is not transparent enough, where we can not know the dependency and independency of column operations. And through yw model, it classify Openrefine operations into two levels: schema level and column level. 

1.Repo Structure
------------------

1.1 or2yw_examples

folder          |  Description
----------------|------------
Ecology_rodents |  [Portal_rodents_19772002_scinameUUIDs.csv](https://ndownloader.figshare.com/files/7823341)
NYPL            |  [What's on the Menu?](http://menus.nypl.org/data)



Take NYPL folder as an example:

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

1.2 or2ywtool 

This tool is aimed to connect OpenRefine Recipe which is written in JSON format with Yesworkflow, where it can generate the Parallel and Serial conceptual model. And in this way, the depedency relationships between each data cleaning steps can be shown clearly.





2.Toolkit Usage
----------------
1. Python Version : 3+
  
  Install the or2yw package from pip install: 
     
       $ pip  install upgrade --index-url https://test.pypi.org/simple/ or2ywtool

(Note: double check the pip version, if pip is for version 2, then use pip3 install...)

2. After successfully install the or2yw tool, there are two ways using this tool.

2.1 Generate yw file , copy and paste on Yesworkflow Editor (No need to install other dependency packages)

       $ python -m or2ywtool
         usage: __main__.py [-h] [-i INPUT] [-o OUTPUT] [-t TYPE] [-ot OUTPUTTYPE]
                   [-j JAVA] [-dot DOT] [-title TITLE] [-desc DESCRIPTION]

          OR2YW v0.0.1

          optional arguments:
            -h, --help            show this help message and exit
            -i INPUT, --input INPUT
                                  openrefine json file
            -o OUTPUT, --output OUTPUT
                                  yesworkflow output file
            -t TYPE, --type TYPE  Workflow Type, Produce [serial,parallel] workflow,
                                  Default: serial
            -ot OUTPUTTYPE, --outputtype OUTPUTTYPE
                                  Output Type, Produce output [yw,gv,png,svg,pdf],
                                  Default: yw (only yw for now other file type will
                                  available in the next release)
            -j JAVA, --java JAVA  Java Path, if not initialized will use the java
                                  installation environment path
            -dot DOT, --dot DOT   Dot Path, if not initialized will use the dot
                                  installation environment path
            -title TITLE, --title TITLE
                                  Title for the Workflow
            -desc DESCRIPTION, --description DESCRIPTION
                                  Description for the Workflow

   a. Generate Serial yw file:
      
       $ python -m or2ywtool -i or2ywtool/test.json -o test.yw -t 
   
   b. Generate Parallel yw file:
       
       $ python -m or2ywtool -i or2ywtool/test.json -o test.yw -t parallel
       
   c. Test on Yesworkflow Editor: [Yesworkflow](http://try.yesworkflow.org/)
       
2.2  Generate pdf/png with tool. (**Require Graphviz install)
   
   a. Check your graphviz version:
      
     $ dot -V 
     
   b. Install the latest version:
   
   1). For Mac users (use Homebrew):
    
    $ brew install graphviz
    
   2). For Windows users ():
   
   
   3). For Linux users():
   
   
   c. Use the command to generate the Yesworkflow PDF/PNG file (insert the json file in the correct path, and the output file name):
   
   ex1. Generate **Parallel Yesworkflow model PDF file:
   
    $ python -m or2ywtool -i or2ywtool/test.json -o testa.pdf -ot pdf -t parallel
   
   ex2. Generate **Parallel Yesworkflow model PNG file:
   
    $ python -m or2ywtool -i or2ywtool/test.json -o testa.png -ot png -t parallel
    
   ex3. Generate **Linear Yesworkflow model PDF file:
     
    $ python -m or2ywtool -i or2ywtool/test.json -o testa.pdf -ot pdf
    
   ex4. Generate **Linear Yesworkflow model PNG file:
    
    $ python -m or2ywtool -i or2ywtool/test.json -o testa.png -ot png
   
    

  


