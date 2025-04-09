import requests


def getProjects(host):
    response = requests.get(f"{host}/projects?page%5Bsize%5D=1000") 
    # default page size is 100, to get all projects, we need to set the page size to a large number
    if response.status_code != 200:
        raise Exception(f"Server returned code {response.status_code}")
    return response.json()

def getProject(host, project):
    response = requests.get(f"{host}/projects/{project}?page%5Bsize%5D=1000") 
    if response.status_code != 200:
        raise Exception(f"Server returned code {response.status_code}") 
    return response.json()

def getHeadCommit(host, project):
    response=requests.get(f"{host}/projects/{project}/branches")
    if response.status_code != 200:
        raise Exception("Server returned code " + response.status_code) 
    return response.json()[0]['head']['@id']

def getElements(host, project, commit=None):
    if commit is None:
        commit = getHeadCommit(host, project)
    response = requests.get(f"{host}/projects/{project}/commits/{commit}/elements?page%5Bsize%5D=1000")
    if response.status_code != 200:
        raise Exception(f"Server returned code {response.status_code}") 
    return response.json()

def getElementsAsString(host, project, commit=None):
    # returns the elements of the given project as multiline string
    # in the format
    # «{element_type}» {declared_name}
    elementsAsString = ""
    elements = getElements(host, project, commit)
    for element in elements:
        declared_name = element["declaredName"]
        element_type = element["@type"]
        text = f"«{element_type}» {declared_name}\n"
        elementsAsString += text
    return elementsAsString

def deleteProject(host, project):
    print (f"{host}/projects/{project}")
    response = requests.delete(f"{host}/projects/{project}")
    if response.status_code != 204:
        raise Exception(f"Server returned code {response.status_code}")

def getParts(host,project, commit=None):
    # returns the part definitions of the given project as a list of dictionaries
    # each dictionary has the keys 'name' and 'id'
    parts = []
    elements = getElements(host, project, commit)
    for element in elements:
        if element["@type"] == "PartDefinition":
            parts.append({"name":element["declaredName"],"id":element["@id"]})
    return parts

def getExchangeID(host, project):
    query = {
        '@type':'Query',
        'select': ['@id'],
        'where': {
            '@type': 'CompositeConstraint',
            'operator': 'and',
            'constraint': [
                {
                    '@type': 'PrimitiveConstraint',
                    'inverse': False,
                    'operator': '=',
                    'property': 'declaredName',
                    'value': 'Exchange'
                },
                {
                    '@type': 'PrimitiveConstraint',
                    'inverse': False,
                    'operator': '=',
                    'property': '@type',
                    'value': 'AttributeDefinition'
                }
            ]
            }
        }
    query_url = f"{host}/projects/{project}/query-results" 
    response = requests.post(query_url, json=query)

    if response.status_code != 200:
         raise Exception(f"Server returned code {response.status_code}") 

    query_response_json = response.json()
 
    #returns the ID of the attribute definition exchange
    return query_response_json[0]['@id']
 
