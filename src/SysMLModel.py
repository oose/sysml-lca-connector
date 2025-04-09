# a class representing a SysML model

from SysMLAPI import getProject, getElements

def listToDictonary(input: list) -> dict:
    # uses the @id as key for the dictionary
    return {element['@id']:element for element in input}

class SysMLModel:
    host=""
    project=""
    commit=None
    theModel={}
    name=""

    def __init__(self, host, project, commit=None):
        self.host=host
        self.project=project
        self.commit = commit
        projectData=getProject(host,project)
        self.name=projectData.get('name')
        self.theModel =listToDictonary(getElements(host,project,commit))
        print ("model size = ",len(self.theModel))

    def getElements(self):
        return self.theModel
    
    def findElementId(self, name, type):
        for element in self.theModel.values():
            if element['name'] == name and element['@type'] == type:
                return element['@id']
        return None

    def getElementbyId(self, id):
        return self.theModel[id]

    def getElement(self,reference):
        if reference:
            return self.theModel[reference.get('@id')]

    def getDirectSubclasses(self,superclass):
        result={}
        for element in self.theModel.values():
            if self.isDirectSubclass(element, superclass):
                result[element['@id']]=element
        return result
        
    def isDirectSubclass(self, element, superclass):
        if element.get('ownedSubclassification'):
            for sub in element['ownedSubclassification']:
                general=self.getElement(sub)['general']
                return general['@id']==superclass
            
    def getMetaChain(self,element,metachain):
        """
        Retrieves the element(s) at the end of the metachain.
        Args:
            element (dict): The starting element from which to traverse the metachain.
            metachain (list of lists): A list of lists, where each inner list contains two elements:
                - The type of the element (str).
                - The name of the reference to the next element (str).
        Returns:
            The element(s) at the end of the metachain if found, otherwise None.
        """      
        def isValue(e):
            return not isinstance(e, (list,set,dict))

        wantedType = metachain[0][0]
        attributeName = metachain[0][1]
        if element==None:
            return None
        if isinstance(element,list):
            element=element[0]
        if wantedType==None or element['@type']==wantedType:
            if isValue( element[attributeName]): 
                # a value is never referencing another element
                if len(metachain)==1:
                    return element[attributeName]    
                else:
                    return None # if we are not at the end of the chain, the value is not what we are looking for
            elif isinstance(element[attributeName],dict): 
                # expected: reference to another element, just one entry for @id
                subelement=self.getElement(element[attributeName])
                if len(metachain)==1:
                    return subelement
                else:
                    return self.getMetaChain(subelement,metachain[1:])
            elif isinstance(element[attributeName],list):
                # expected: list of references to other elements
                listOfSubelements=[]
                for subElementReference in element[attributeName]: 
                    subelement=self.getElement(subElementReference)
                    listOfSubelements.append(subelement)
                if len(listOfSubelements)==0: listOfSubelements=None
                if len(metachain)==1:
                    return listOfSubelements
                else:
                    return self.getMetaChain(listOfSubelements,metachain[1:])
            else:
                return None  

        else:
            return None

    def getSubsettedFeatures(self,element):
        # ownedSubsetting.subsettedFeature
        return self.getMetaChain(element,[[None,'ownedSubsetting'],['Subsetting','subsettedFeature']])        
    
    def getUsedMetadata(self,element):
        # ownedMember.type.ownedMember
        return self.getMetaChain(element,[[None,'ownedMember'],['MetadataUsage','type']])

    def usesMetadata(self, element, metadataID):
        metadataList = self.getUsedMetadata(element)
        if metadataList:
            for metadata in metadataList:
                if metadata['@id'] == metadataID:
                    return True
        return False

    def getElementsWithMetadata(self, type, metadataID):
        result={}
        for element in self.theModel.values():
            if element['@type'] == type:
                if self.usesMetadata(element, metadataID):
                    result[element['@id']]=element
        return result
    
    def filterListByMetadata(self, elements, metadataID):
        result=[]
        if elements:
            for elementRef in elements:
                element=self.getElement(elementRef)
                if self.usesMetadata(element,metadataID):
                    result.append(element)
        return result

    def getOwnedMembersWithType(self,element,typeList):
        result=[]
        for member in element['ownedMember']:
            ownedmember=self.getElement(member)
            if ownedmember['@type'] in typeList:
                result.append(ownedmember)
        return result

    def getMultiplicity(self,feature):
        # cases
        # no explicit multiplicity: Type is not Multiplicity 
        # explicit multiplicity: Type is MultiplicityRange 
        # only one value: lowerBound is empty
        # both values: lowerBound and upperBound are present

        multiplicityElement = self.getElement(feature.get('multiplicity', {}))
        if multiplicityElement is None:
            return {'lowerBound': None, 'upperBound': None}
        elif multiplicityElement['@type']=='MultiplicityRange':
            lowerBound=self.getMetaChain(multiplicityElement,[['MultiplicityRange','lowerBound'],['LiteralInteger','value']])# might be empty
            upperBound=self.getMetaChain(multiplicityElement,[['MultiplicityRange','upperBound'],['LiteralInteger','value']])
            if not lowerBound: lowerBound=upperBound
        elif multiplicityElement['@type']=='Multiplicity':
            lowerBound=1 # the default
            upperBound=1
        return {'lowerBound':lowerBound,'upperBound':upperBound}

    def getDefaultValue(self,attributeUsage):
        # cases
        # 1. positive numerical value:   ownedMember.value
        # 2. negative numerical value: - ownedMember.argument[0].value for operator "-"
        # 3. positive scalar value:      ownedMember.argument[0].value for operator "[" ownedMember.argument[1].referent 
        # 4. negative scalar value:    - ownedMember.argument[0].argument[0].value for operator "-" ownedMember.argument[0].argument[1].referent
        element=self.getOwnedMembersWithType(attributeUsage,['LiteralInteger','LiteralRational','OperatorExpression'])[0]
        # assumption: there is only one member of the types

        sign=1
        if element['@type']=='OperatorExpression':
            operator=element['operator']
            if operator == '-': # negation operator
                element=self.getElement(element['argument'][0])
                sign = -1
        
        if element['@type'] in ['LiteralInteger','LiteralRational']: 
            return {'num':sign * element['value'],'mRef':None}
        elif element['@type']=='OperatorExpression':
            operator=element['operator']
            if operator=='[': # ScalarQuantityValue Construction operator
                argument0=self.getElement(element['argument'][0])
                argument1=self.getElement(element['argument'][1])
                return {'num':sign * argument0['value'],'mRef':argument1['referent']}
            
    def asHTML(self):
        def getName(element):
            # if the element doesn't have a name, return the last 5 characters of the id
            return element.get('name') if element.get('name') else f"…{element['@id'][-5:]}"
            #return element.get('name',f"…{element['@id'][-5:]}")

        def getHtmlReference(element):
            try:
                element= element if element.get('@type') else self.theModel[element['@id']]
                return f"<span class=\"metaclass\">«{element.get('@type')}»</span> <a href=\"#{element.get('@id')}\">{getName(element)}</a>"
            except:
                return ""

        def getValues(element,attributeName):
            result=""   
            try:
                if element.get(attributeName):
                    result=f"<h4>{attributeName}</h4>\n"
                    if isinstance(element[attributeName],str):
                        result+=f"<p>\"{element[attributeName]}\"</p>\n"    
                    elif isinstance(element.get(attributeName),dict):
                        element=self.theModel[element[attributeName]['@id']]
                        result+=f"<p>{getHtmlReference(element)}</p>\n"
                    elif isinstance(element.get(attributeName), bool):
                        result+=f"<p>{element[attributeName]}</p>\n"
                    elif isinstance(element.get(attributeName), int):
                        result+=f"<p>{element[attributeName]}</p>\n"
                    elif isinstance(element.get(attributeName), float):
                        result+=f"<p>{element[attributeName]}</p>\n"
                    else:
                        for e in element.get(attributeName,[]):
                            theElement=self.theModel.get(e['@id'])
                            if theElement:
                                result+=f"<p>{getHtmlReference(theElement)}</p>\n"
                            else:
                                result+=f"<p>{e}</p>\n"
            except Exception as ex:
                print(f"Error in getValues: {attributeName} - {ex}")
            return result

        def isReference(element):
            # element is of {'@id': 'xyz} form
            return isinstance(element,dict) and element.get('@id')
        
        print("asHTML")
        s=f"<!doctype html><html><head><meta charset=\"UTF-8\"><title>{self.name}</title>"
        s+="""
        <style>@import url('https://fonts.googleapis.com/css2?family=Roboto+Mono&display=swap');
        body {font-family: 'Roboto Mono', 'Courier New', monospace;} 
        h3 {font-size: 12pt; font-weight: bold;margin-bottom:0;margin-top:6pt;border-top: 1px solid Lightgrey;} 
        h4 {font-size: 9pt; font-weight: bold;margin-top:0;margin-bottom:0;margin-left:2em;} 
        p {font-size: 9pt; margin-left:2em; margin-top:0; margin-bottom:0;}
        summary {font-size: 9pt; font-weight: normal;margin-left:2em;} 
        span.metaclass {font-size: 9pt; font-weight:normal;}</style>
        </head>
        <body>
        """
        visibleFields=['owner','type','ownedSubclassification','superclassifier','ownedMember','argument','operator','referent','body']
        for element in self.theModel.values():
            s+=f"<h3 id=\"{element['@id']}\"><span class=\"metaclass\">«{element['@type']}»</span>&nbsp;{getName(element)}"
            if element.get('value'):
                if isReference(element['value']):
                    s+=f"&nbsp;=&nbsp;{getHtmlReference(element['value'])}"
                else:
                    s+=f"&nbsp;=&nbsp;{element['value']}"
            s+="</h3>\n"
            for f in visibleFields:
                s+=getValues(element,f)
            s += f"<details><summary>more…</summary>"
            for subelement in element:
                if subelement not in set(visibleFields).union({'@id','@type','name','qualifiedName','elementId'}):
                    s += getValues(element, subelement)
            s += "</details>\n"
        s+="</body></html>"
        print(s)
        return s     
