# a class representing a SysML model

from SysMLAPI import getProject, getElements, PAGE_SIZE_FOR_ELEMENTS

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
        print ("model loaded \n size = ",len(self.theModel))
        if len(self.theModel)==PAGE_SIZE_FOR_ELEMENTS:
            print(f"Warning: the model contains exactly {PAGE_SIZE_FOR_ELEMENTS} elements. It probably hit the page size limit. Consider increasing the page size in the API call.")

    def getElements(self):
        return self.theModel
    
    def findElementId(self, name, type):
        for element in self.theModel.values():
            if element.get('declaredName') == name and element['@type'] == type:
                return element['@id']
        return None

    def getElementbyId(self, id):
        return self.theModel.get(id)

    def getElement(self,reference):
        if reference and reference.get('@id'):
            return self.theModel.get(reference['@id'])

    def getDirectSubclasses(self,superclass):
        result={}
        for element in self.theModel.values():
            if self.isDirectSubclass(element, superclass):
                result[element['@id']]=element
        return result
        
    def isDirectSubclass(self, element, superclass):
        if element.get('ownedSubclassification'):
            for sub in element['ownedSubclassification']:
                subElement = self.getElement(sub)
                if subElement and subElement.get('general'):
                    if subElement['general'].get('@id') == superclass:
                        return True
        return False
            
    def getMetaChain(self,element,metachain,resulttype:list=None):
        """
        Retrieves the element(s) at the end of the metachain.
        Args:
            element (dict): The starting element from which to traverse the metachain.
            metachain (list of lists): A list of lists, where each inner list contains two elements:
                - The type of the element (str).
                - The name of the reference to the next element (str).
            resulttype (list, optional): A list of accepted types for the resulting element(s). If provided, only elements whose @type is in the list are returned.
        Returns:
            The element(s) at the end of the metachain if found, otherwise None.
        """      
        def isValue(e):
            return not isinstance(e, (list,set,dict))

        wantedType = metachain[0][0]
        attributeName = metachain[0][1]
        if element is None:
            return None
        if isinstance(element, list):
            results = [self.getMetaChain(e, metachain, resulttype) for e in element if e is not None]
            results = [item for r in results for item in (r if isinstance(r, list) else [r]) if item is not None]
            return results if results else None
        if wantedType==None or element['@type']==wantedType:
            if attributeName not in element:
                return None
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
                    if resulttype is not None and isinstance(subelement, dict) and subelement.get('@type') not in resulttype:
                        return None
                    return subelement
                else:
                    return self.getMetaChain(subelement,metachain[1:],resulttype)
            elif isinstance(element[attributeName],list):
                # expected: list of references to other elements
                listOfSubelements=[]
                for subElementReference in element[attributeName]:
                    subelement=self.getElement(subElementReference)
                    listOfSubelements.append(subelement)
                if len(listOfSubelements)==0: listOfSubelements=None
                if len(metachain)==1:
                    if resulttype is not None and listOfSubelements is not None:
                        listOfSubelements = [e for e in listOfSubelements if isinstance(e, dict) and e.get('@type') in resulttype]
                        if len(listOfSubelements)==0: listOfSubelements=None
                    return listOfSubelements
                else:
                    return self.getMetaChain(listOfSubelements,metachain[1:],resulttype)
            else:
                return None  

        else:
            return None

    def getSubsettedFeatures(self,element):
        # ownedSubsetting.subsettedFeature
        # return self.getMetaChain(element,[[None,'ownedSubsetting'],['Subsetting','subsettedFeature']]) only works if the repository contains derived values.       
        return self.getMetaChain(element,[[None,'ownedRelationship'],['Subsetting','subsettedFeature']])        
    
    def getUsedMetadata(self,element):
        # ownedMember.type.ownedMember
        #return self.getMetaChain(element,[[None,'ownedMember'],['MetadataUsage','type']])
        # this would only work, if derived fields have been stored.
        return self.getMetaChain(element,[[None,'ownedRelationship'],['OwningMembership','target'],
                                        ['MetadataUsage','ownedRelationship'],['FeatureTyping','type']]) 

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

    def getOwnedFeaturesWithType(self, element, typeList):
        return self.getMetaChain(element,[[None,'ownedRelationship'],['FeatureValue','target']],typeList)

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

    def getArguments(self, element):
        # returns the arguments of an element like OperatorExpression
        return self.getMetaChain(element,[[None,'ownedRelationship'],['ParameterMembership','target' ], 
            ['Feature','ownedRelationship'],['FeatureValue','target']])

    def getReferent(self, featureReferenceExpression):
        # returns the referent of a feature reference expression like ScalarQuantityValue
        return self.getMetaChain(featureReferenceExpression,[[None,'ownedRelationship'],['Membership','target']])

    def getDefaultValue(self,attributeUsage):
        # cases
        # 1. positive numerical value:   ownedMember.value
        # 2. negative numerical value: - ownedMember.argument[0].value for operator "-"
        # 3. positive scalar value:      ownedMember.argument[0].value for operator "[" ownedMember.argument[1].referent 
        # 4. negative scalar value:    - ownedMember.argument[0].argument[0].value for operator "-" ownedMember.argument[0].argument[1].referent
        candidates = self.getOwnedFeaturesWithType(attributeUsage, ['LiteralInteger','LiteralRational','OperatorExpression'])
        if not candidates:
            return None
        element = candidates[0]

        sign=1
        if element['@type']=='OperatorExpression':
            operator=element['operator']
            if operator == '-': # negation operator
                element=self.getArguments(element)[0] # there is only one argument for the negation operator
                sign = -1
        
        if element['@type'] in ['LiteralInteger','LiteralRational']: 
            return {'num':sign * element['value'],'mRef':None}
        elif element['@type']=='OperatorExpression':
            operator=element['operator']
            if operator=='[': # ScalarQuantityValue Construction operator
                argument=self.getArguments(element)
                
                return {'num':sign * argument[0]['value'],'mRef':self.getReferent(argument[1])[0]}
            
    def asHTML(self):
        def getName(element):
            # if the element doesn't have a name, return the last 5 characters of the id
            return (element.get('name') or element.get('declaredName') or element.get('shortName') or
                    element.get('memberName') or element.get('memberShortName') or f"…{element['@id'][-5:]}")

        def getHtmlReference(element):
            try:
                element= element if element.get('@type') else self.theModel[element['@id']]
                return f"<span class=\"metaclass\">«{element.get('@type')}»</span> <a href=\"#{element.get('@id')}\">{getName(element)}</a>"
            except:
                return ""

        def getValues(element,attributeName):
            parts=[]
            try:
                if element.get(attributeName):
                    theAttribute=element[attributeName]
                    parts.append(f"<h4>{attributeName}</h4>\n")
                    if isinstance(theAttribute,str):
                        parts.append(f"<p>\"{theAttribute}\"</p>\n")
                    elif isinstance(theAttribute,dict):
                        # expected: reference to another element, just one entry for @id
                        el=self.theModel.get(theAttribute['@id'])
                        if el:
                            parts.append(f"<p>{getHtmlReference(el)}</p>\n")
                        else:
                            parts.append(f"<p>{theAttribute['@id']}</p>\n")
                    elif isinstance(theAttribute, (bool, int, float)):
                        parts.append(f"<p>{theAttribute}</p>\n")
                    else:
                        # expected: list of references to other elements or list of strings
                        for e in element.get(attributeName,[]):
                            if isinstance(e, str):
                                parts.append(f"<p>\"{e}\"</p>\n")
                            elif isinstance(e, dict):
                                theElement=self.theModel.get(e['@id'])
                                if theElement:
                                    parts.append(f"<p>{getHtmlReference(theElement)}</p>\n")
                                else:
                                    parts.append(f"<p>{e['@id']}</p>\n")
                            else:
                                parts.append(f"<p>unexpected type of {e}</p>\n")
            except Exception as ex:
                print(f"Error in getValues: {attributeName} - {ex}")
            return "".join(parts)

        def isReference(element):
            # element is of {'@id': 'xyz} form
            return isinstance(element,dict) and element.get('@id')

        def isExternal(element):
            # detect external elements:
            # has only one property with Value: isLibraryElement==true
            if not isinstance(element, dict):
                return False
            meaningful = [k for k, v in element.items() if v is not None and v != [] and k not in ['@id','@type','name','qualifiedName','elementId']]
            return meaningful == ['isLibraryElement'] and element.get('isLibraryElement') is True
        
        print("asHTML")
        parts=[f"<!doctype html><html><head><meta charset=\"UTF-8\"><title>{self.name}</title>"]
        parts.append("""
        <style>@import url('https://fonts.googleapis.com/css2?family=Roboto+Mono&display=swap');
        body {font-family: 'Roboto Mono', 'Courier New', monospace;}
        h3 {font-size: 12pt; font-weight: bold;margin-bottom:0;margin-top:6pt;border-top: 1px solid Lightgrey;}
        h4 {font-size: 9pt; font-weight: bold;margin-top:0;margin-bottom:0;margin-left:2em;}
        p {font-size: 9pt; margin-left:2em; margin-top:0; margin-bottom:0;}
        summary {font-size: 9pt; font-weight: normal;margin-left:2em;}
        span.metaclass {font-size: 9pt; font-weight:normal;}</style>
        </head>
        <body>
        """)
        visibleFields=['owner','type','ownedSubclassification','superclassifier','ownedMember','argument','operator','referent','body']
        for element in self.theModel.values():
            parts.append(f"<h3 id=\"{element['@id']}\"><span class=\"metaclass\">«{element['@type']}»</span>&nbsp;{getName(element)}")
            if element.get('value'):
                if isReference(element['value']):
                    parts.append(f"&nbsp;=&nbsp;{getHtmlReference(element['value'])}")
                else:
                    parts.append(f"&nbsp;=&nbsp;{element['value']}")
            if isExternal(element):
                parts.append(f"&nbsp;<span class=\"metaclass\">[external]</span>") 
                parts.append("</h3>\n")
            else: 
                parts.append("</h3>\n")
                for f in visibleFields:
                    parts.append(getValues(element,f))
                parts.append("<details><summary>more…</summary>")
                for subelement in element:
                    if subelement not in set(visibleFields).union({'@id','@type','name','qualifiedName','elementId'}):
                        parts.append(getValues(element, subelement))
                parts.append("</details>\n")
        parts.append("</body></html>")
        s = "".join(parts)
        with open("model.api.html", "w", encoding="utf-8") as f:
            f.write(s)
        print ("model.api.html created")
        return s     
