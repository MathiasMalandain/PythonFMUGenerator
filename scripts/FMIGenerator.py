# Implementation of class FMIGenerator
#
# This file is part of FMICodeGenerator (https://github.com/ghorwin/FMICodeGenerator)
#
# BSD 3-Clause License
#
# Copyright (c) 2018, Andreas Nicolai
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
# * Neither the name of the copyright holder nor the names of its
#   contributors may be used to endorse or promote products derived from
#   this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import os
import sys
import shutil
from shutil import *
import uuid
import time
import subprocess
import datetime
import platform
from third_party.send2trash_master.send2trash import send2trash

# The directory name of the template folder
TEMPLATE_FOLDER_NAME = "FMI_template"

class FMIGenerator():
	"""Class that encapsulates all parameters needed to generate the FMU.

	Usage: create class instance, set member variables, call function generate()
	"""

	def __init__(self):
		""" Constructor, initializes member variables.

		Member variables:
		
		targetDir -- Target directory can be relative (to current working directory) or
					 absolute. FMU directory is created below this directory, for example:
					    <target path>/<modelName>/
					 By default, target path is empty which means that the subdirectory <modelName>
					 is created directly below the current working directory.
		modelName -- A user defined model name
		description -- A user defined description
		inputVars -- vector of type VarDefs with input variable definitions 
		outputVars -- vector of type VarDefs with output variable definitions 
		parameters -- vector of type VarDefs with parameter definitions 
		"""
		self.targetDir = ""
		
		self.modelName = ""
		self.description = ""
		self.inputVars = []
		self.outputVars = []
		self.parameters = []

	def generate(self):

		""" Main FMU generation function. Requires member variables to be set correctly.

		Functionality: first a template folder structure is copied to the target location. Then,
		placeholders in the original files are substituted.
		
		Target directory is generated using targetDir member variable, for relative directory, 
		the target directory is created from `<current working directory>/<targetDir>/<modelName>`.
		For absolute file paths the target directory is `<targetDir>/<modelName>`.
        """

		# sanity checks
		if self.modelName == "":
			raise RuntimeError("Missing model name")

		# compose target directory: check if self.targetPath is an absolute file path
		if (os.path.isabs(self.targetDir)):
			self.targetDirPath = ps.path.join(self.targetDir, self.modelName)
		else:
			self.targetDirPath = os.path.join(os.getcwd(), self.targetDir)
			self.targetDirPath = os.path.join(self.targetDirPath, self.modelName)

		print("Target directory   : {}".format(self.targetDirPath))

		# the source directory with the template files is located relative to
		# this python script: ../data/FMIProject

		# get the path of the current python script
		scriptpath = os.path.abspath(os.path.dirname(sys.argv[0]))
		print("Script path        : {}".format(scriptpath))

		# relative path (from script file) to resource/template directory
		templateDirPath = os.path.join(scriptpath, "../data/" + TEMPLATE_FOLDER_NAME)
		templateDirPath = os.path.abspath(templateDirPath)
		print("Template location  : {}".format(templateDirPath))

		# user may have specified "FMI_template" as model name 
		# (which would be weird and break the code, hence a warning)
		if self.modelName == "FMI_template":
			print("WARNING: model name is same as template folder name. This may not work!")
			
		print("Copying template directory to target directory (and renaming files)")
		self.copyTemplateDirectory(templateDirPath)
		
		print ("Adjusting template files (replacing placeholders)")
		self.subtitutePlaceholders()

		print ("Test-building FMU")
		#self.testBuild()
		
		# *** Done with FMU generation ***



	def copyTemplateDirectory(self, templatePath):
		"""Copies the template folder to the new location. Replaces the old name of directories, files 
		and script in the files with the newly user defined name (i.e.modelName).
		
		Path to target directory is stored in self.targetDirPath.
		If target directory exists already, it is moved to trash first.

		Const-function, does not modify the state of the object.

		Arguments:

		templatePath -- The absolute path to the template directory.
		
		Example:
		
		```python
		self.copyTemplateDirectory("../data/FMI_template")
		
		# will rename "FMI_template" to "testFMU" after copying
		```
		"""


		try:
			# check if target directory exists already
			if os.path.exists(self.targetDirPath):
				# Move folder to thrash
				send2trash(self.targetDirPath)
				
			# Copy source folder to a new location(i.e. self.targetDirPath)
			shutil.copytree(templatePath, self.targetDirPath)
			# Set modified time of newly created folder
			os.utime(self.targetDirPath, None)
		except:
			raise RuntimeError("Cannot copy template directory to target directory")

		try:
			# rename files that must be named according as the modelName
			os.rename(self.targetDirPath + "/projects/Qt/" + TEMPLATE_FOLDER_NAME + ".pro", 
			          self.targetDirPath + "/projects/Qt/" + self.modelName + ".pro")
			os.rename(self.targetDirPath + "/src/" + TEMPLATE_FOLDER_NAME + ".cpp", 
			          self.targetDirPath + "/src/" + self.modelName + ".cpp")
			os.rename(self.targetDirPath + "/src/" + TEMPLATE_FOLDER_NAME + ".h", 
			          self.targetDirPath + "/src/" + self.modelName + ".h")
		except:
			raise RuntimeError("Cannot rename template files")


	def subtitutePlaceholders(self):  
		"""Processes all template files and replaces placeholders within the files with generated values.
		
		1. It generates globally unique identifier
		2. It generates local time
		3. It replaces placeholders.

		"""

		# Generate globally unique identifier
		guid = uuid.uuid1()

		# Generate local date and time
		localtime = time.strftime('%Y-%m-%dT%I:%M:%SZ',time.localtime())

		# Path to check the name of the directories, files, script in files in new folder  
		src = ""
		# Path refering the directories, files, script in files after renaming in new folder
		dst = ""

		# loop to walk through the new folder  
		for root, dircs, files in os.walk(targetDir,oldName):
			# loop to replace the old name of directories into user defined new name(i.e modelName)
			os.utime(root,None)
			for dirc in dircs:
				if oldName in dirc:
					# compose full path of old named directory inside the new folder
					src = os.path.join(root,dirc)
					# compose full path of newly named directory inside new folder
					dst = os.path.join(root,dirc.replace(oldName, self.modelName))
					os.rename(src,dst)


			# loop to replace the old name of files and in script into a new name (i.e.modelName)  
			for file in files:

				# compose full file path
				src = os.path.join(root,file)

				# read file into memory, variable 'data'
				fobj = open(src,'r')
				data = fobj.read()
				fobj.close()

				# generic data adjustment
				data = data.replace(oldName,self.modelName)            


				# process data depending on file type
				if file == "modelDescription.xml":
					data = self.adjustModelDescription(data, localtime, guid)

				if file=="FMIProject.cpp":
					data = data.replace("$$GUID$$", str(guid))            

				#finally, write data back to file

				fobj=open(src,'w')
				fobj.write(data)
				fobj.close()

				if oldName in file:
					dst = os.path.join(root,file.replace(oldName, self.modelName))
					os.rename(src,dst)
					print("'{}' renamed" .format(file))






	def adjustModelDescription(self, data, time, guid):
		""" defined function to to replace modelName, description, date and time, and GUID in file script 
		and returns the modified memory, variable 'data'.

		Arguments:

		data -- read file into memory
		time -- generated localtime(format:2018-09-13T11:59:46Z)
		guid -- globally unique identifier
		"""
		self.data = data
		self.time = time
		self.guid = guid

		data = data.replace("$$dateandtime$$",time)
		data = data.replace("$$GUID$$", str(guid))        
		data = data.replace("$$description$$", self.description)
		data = data.replace("$$modelName$$",self.modelName)    

		return data 



	def testBuildFMU(self, targetDir):
		# generate path to /build subdir
		bindir = targetDir + "/build"
	
		try:
			# Check for the platform on which the shell script will execute
			# Shell file execution for Windows
	
			print("Test-building the FMU. You should first implement your FMU functionality before using the FMU!")
			if platform.system() == "Windows":
				# start the external shell script to build the FMI library
				pipe = subprocess.Popen(["bash", './build.sh'], cwd = bindir, stdout = subprocess.PIPE, stderr = subprocess.PIPE)                
				# retrieve output and error messages
				outputMsg,errorMsg = pipe.communicate()  
				# get return code
				rc = pipe.returncode 
	
				# if return code is different from 0, print the error message
				if rc != 0:
					print "Error during compilation of FMU"
					print errorMsg
					return
				else:
					print "Compiled FMU successfully"
	
				# renaming file    
				binDir = targetDir + "/bin/release"
				for root, dircs, files in os.walk(binDir):
					for file in files:
						if file == 'lib'+ self.modelName + '.so.1.0.0':
							oldFileName = os.path.join(binDir,'lib'+ self.modelName + '.so.1.0.0')
							newFileName = os.path.join(binDir,self.modelName + '.dll')
							os.rename(oldFileName,newFileName)
	
	
				deploy = subprocess.Popen(["bash", './deploy.sh'], cwd = bindir, stdout = subprocess.PIPE, stderr = subprocess.PIPE)                           
				outputMsg,errorMsg = deploy.communicate()  
				dc = deploy.returncode             
	
				if dc != 0:
					print "Error during compilation of FMU"
					print errorMsg
					return
				else:                    
					print "Compiled FMU successfully"	                 
	
			else:
				# shell file execution for Mac & Linux
				pipe = subprocess.Popen(["bash", './build.sh'], cwd = bindir, stdout = subprocess.PIPE, stderr = subprocess.PIPE)                           
				outputMsg,errorMsg = pipe.communicate()  
				rc = pipe.returncode             
	
				if rc != 0:
					print "Error during compilation of FMU"
					print errorMsg
					return
				else:                    
					print "Compiled FMU successfully"
	
				binDir = targetDir + "/bin/release"
				for root, dircs, files in os.walk(binDir):
					for file in files:
						if file == 'lib'+ self.modelName + '.so.1.0.0':
							oldFileName = os.path.join(binDir,'lib'+ self.modelName + '.so.1.0.0')
							# chnage of file extension depending on type of platform
							if platform.system() == 'Darwin':
								newFileName = os.path.join(binDir,self.modelName + '.dylib')
							else:
								newFileName = os.path.join(binDir,self.modelName + '.so')
							os.rename(oldFileName,newFileName)
	
				# shell file execution for Mac & Linux
				deploy = subprocess.Popen(["bash", './deploy.sh'], cwd = bindir, stdout = subprocess.PIPE, stderr = subprocess.PIPE)                           
				outputMsg,errorMsg = deploy.communicate()  
				dc = deploy.returncode             
	
				if dc != 0:
					print "Error during compilation of FMU"
					print errorMsg
					return
				else:                    
					print "Compiled FMU successfully"	
	
		except OSError as e:
			print "Error executing 'bash' command line interpreter."
			return

