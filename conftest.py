import pytest
import docker
import sys
import pytest
import re
import os 

#command_result_dict={ "Rscript app.R":"Rplot001.svg" , "Rscript -e model.R":["Rplot001.svg"] , "Rscript -e main.R":["Rplot001.svg"] , "python main.py":["myHistogramFromPython.png"] ,"Rscript -e iris.R":["Rplot001.svg"],  "python iris.py":["iris.png"] }
command_result_dict={ "Rscript app.R":["Rplot001.svg"] , "Rscript -e model.R":["Rplot001.svg"] , "Rscript -e main.R":["Rplot001.svg"] , "python main.py":["myHistogramFromPython.png"] ,"Rscript -e iris.R":["Rplot001.svg"],  "python iris.py":["iris.png"] }
workspace_scripts=[ "jupyterlab/start" , "jupyter/start" , "rstudio/start" , "vscode/start" , "Jupyterlab/start.sh"]
#pytest.set_trace() 
vol_mount =   ['/home/user/DominoData/DOM-32388/domino-develop/skeletons/quick-start:/quick-start' ] 
extra_variables = { 'DOMINO_PROJECT_OWNER':'mjoshi' , 'DOMINO_PROJECT_NAME':'DSE_PROJECT' , 'DOMINO_RUN_ID':'1234' , 'DOMINO_WORKING_DIR':'/mnt'}
container_name='DSE'
DSE_PORTS={'8888/tcp': 8888}


def pytest_addoption(parser):
    parser.addoption( "--image_name", action="store", default="quay.io/domino/standard-environment", help="image repository: quay.io/domino/standard-environment")
    parser.addoption ("--tag_name", action="store", default="latest", help="image tag: latest or anything" )

def check_image_status(image_list , image_name):
  for image in image_list:
    if len(image.tags) != 0:
      if image.tags[0] == image_name:
        return True
  return False

def command_exec ( container , command , expected_output ):
  container.exec_run("bash -c \"rm -f results/*;" + command + "; ls -ltr results \"", workdir='/quick-start')
  str_out= container.exec_run("bash -c \"ls  /quick-start/results\"", workdir='/quick-start')
  print ( str_out.output)
  #print ( str_out.output).decode("utf-8") 
  for output_string in expected_output:
    #if (bool(re.search(output_string ,str(str_out.output)))):
    if ((str(str_out.output, 'UTF-8').strip()) == output_string):
      print(output_string +" found\n")
    else:
      print(output_string +" not found hence test failure\n")
      return False
  return True






@pytest.fixture
def setUp(request):
    #image_name="quay.io/domino/standard-environment:latest"
    image_name = request.config.option.image_name
    print(image_name)
    if image_name is None:
        pytest.skip()
    tag_name = request.config.option.tag_name
    if tag_name is None:
        pytest.skip()
    global container
    client = docker.from_env()
    # Pull the image from registry 
    print ( "Pull the Image" )
    image_name=image_name+":"+tag_name
    print(image_name)
    image = client.images.pull(image_name,'latest')

    print ("Verify the image in local repo")
    image_status = check_image_status(client.images.list() ,image_name)
    if ( image_status is True ):
       print ( image_name+ " Image successfully pulled and is available locally\n")
    else:
       print ( image_name+" Image Not Found")
       sys.exit(1)
    container = client.containers.run(image=image_name, environment=extra_variables ,\
            name=container_name , detach=True, ports=DSE_PORTS ,  \
           volumes=vol_mount , command='/opt/domino/workspaces/Jupyterlab/start.sh' )
                                       
    container.logs()
    yield container
    #test_scripts ( container , command_result_dict)
    print ( "Stop Container")
    print ("Stopping container...\n")

    container.stop()

    print ("Removing container...\n")
    container.remove(v=True, force=True)


def test_scripts(setUp):
  overall_result=True
  for key in command_result_dict:
    script_result=command_exec( container , key , command_result_dict[key] )
    if not ( script_result ):
      overall_result=False
  assert(overall_result) == True 




#@pytest.mark.parametrize('container',indirect=True)
def test_scripts(setUp):
  overall_result=True
  for key in command_result_dict:
    script_result=command_exec( container , key , command_result_dict[key] )
    if not ( script_result ):
      overall_result=False
  assert(overall_result) == True 
 



def test_workspace_scripts(setUp):
  overall_result=True
  base_folder='/opt/domino/workspaces/'
  str_out= container.exec_run("bash -c \"find  "+ base_folder +" -name 'start*'   \"",  workdir='/quick-start')
  script_list = (str(str_out.output, 'UTF-8').strip().split())
  for dir_script in workspace_scripts:
    if base_folder+dir_script not in script_list:
      overall_result=False
  assert(overall_result) == True     


def test_permissions(setUp):
  overall_result=True
  base_folder='/opt/domino/workspaces/'
  str_out= container.exec_run("bash -c \"find  "+ base_folder +" -name 'start*'   \"",  workdir='/quick-start')
  script_list = (str(str_out.output, 'UTF-8').strip().split())
  for dir_script in script_list:
    permissions_out= container.exec_run("python -c \"import os ; status=os.access('" + dir_script +"', os.X_OK); print(status)\"" ,  workdir='/quick-start')
    if not ((str(permissions_out.output, 'UTF-8').strip())):
      overall_result=False