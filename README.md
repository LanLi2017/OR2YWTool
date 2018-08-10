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
1. Go to ../../script/ConfigTool.py; This config file is for users to choose whether to generate Linear or Serial-Parallel yw model. 

You can choose to parse into Linear model

     $ python ConfigTool.py -L 
     
     $ Enter the input file path: 
And Enter the json file path to do the parsing.

After this work is done, 'yw' folder will generate the comments file

2. Using yw command to parse the txt comments file at yw folder

You can use yw command to graph into png file or pdf file:

      $ yw graph yw/Original_LinearParseYW.txt | dot -Tpng -o png/Linear.png && open png/Linear.png

The outputs will be stored in folder png. 

3. Linear && Serial-Parallel yw model:

Linear Model:

![](https://github.com/LanLi2017/OR2YWTool/blob/master/or2yw-examples/Ecology_rodents/results/LinearScreen.png)

Serial-Parallel Model:

![](https://github.com/LanLi2017/OR2YWTool/blob/master/or2yw-examples/Ecology_rodents/results/SPScreen.png)



