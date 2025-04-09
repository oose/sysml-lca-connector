import olca_ipc as openLCA
import olca_schema

numberOfItems="01846770-4cfe-4a25-8ad9-919d8d378345"
# tbd: this is a hack to get the unit for the number of items. The unit should be retrieved from the flow property.
# This only works for the elcd database 

class openLCAServer:
    client=None

    def __init__(self, openLCAServer):
        self.client=openLCA.Client(openLCAServer)

    def getTaggedProcesses(self, tag:str):
        # could be used for tag "from sysml model"
        processes : list[olca_schema.Process] = self.client.get_all(olca_schema.Process)
        # Filter processes by tag property
        filtered_processes = [process for process in processes if process.tags and tag in process.tags]
        return filtered_processes

    def getFlows(self) -> list[olca_schema.Flow]:
        return self.client.get_all(olca_schema.Flow)

    def getTaggedFlows(self, tag:str) -> list[olca_schema.Flow]:
        flows = self.getFlows()
        filtered_flows = [flow for flow in flows if flow.tags and tag in flow.tags]  
        return filtered_flows

    def getSysMLFlowsPackage(self, tag:str):
        flows = self.getTaggedFlows(tag)
        s:str="package openLCAFlows{\n\n"
        s+="    public import openLCA::*;\n\n"
        for flow in flows:
            s+="    attribute '"+flow.name+"' : '"
            if flow.flow_properties:
                for fp in flow.flow_properties:
                    if (fp.is_ref_flow_property):
                        s+=fp.flow_property.name + "'{// reference unit: "+fp.flow_property.ref_unit + "\n"
            else :
                s+="Integer'{\n"
            s+='        @lcaflow{uuid="'+flow.id+'";}\n'
            s+="    }\n\n"
        s+="// attribute definitions for convenience. Just copy them to the appropriate parts of the model\n"
        for flow in flows:
            s+="    #exchg attribute :> '"+flow.name+"'"
            if flow.flow_properties:
                for fp in flow.flow_properties:
                    if (fp.is_ref_flow_property):
                        s+=" = 0 ["+fp.flow_property.ref_unit + "];\n"
            else :
                s+="= 0 [one];\n"

        s+="}"
        return s

    def createProductFlow(self, name:str):    
        flowProperty=self.client.get(olca_schema.FlowProperty, numberOfItems)
        flow = olca_schema.new_flow(name,flow_type=olca_schema.FlowType.PRODUCT_FLOW,flow_property=flowProperty)	
        self.client.put(flow)
        return flow   

    def createProcess(self, partName:str, exchanges:dict[str,dict[float,str]]):
        # returns the uuid of the created process  
        productFlow=self.createProductFlow(partName)
        process = olca_schema.new_process(f"produce {partName}")

        # one instance of the part is produced
        exchange = olca_schema.new_exchange(process, productFlow, 1)
        exchange.is_input = False
        exchange.is_quantitative_reference = True

        for exch in exchanges:    
            flow:olca_schema.FLOW = self.client.get(olca_schema.Flow, exch['id'])
            #u1:olca_schema.UNIT = openLCAClient.get(olca_schema.UnitGroup, "5beb6eed-33a9-47b8-9ede-1dfe8f679159")
            # tbd: unit cannot be found with this method. The standard unit of the flow is used.
            #print(exch['id'],exch['value']['num'],exch['value']['mRef'])
            exchange = olca_schema.new_exchange(process, flow, abs(exch['value']['num']))
            exchange.is_input = exch['value']['num'] < 0
        
        self.client.put(process)
        return process.id
    
    def printListOfFlowPropertiesWithCount(self):
    # how often is a certain flow property used
        flows = self.getFlows()
        flow_property_count = {}
        for flow in flows:
            if flow.flow_properties:
                for fp in flow.flow_properties:
                    # Count the number of added elements with a given name
                    if fp.flow_property.name not in flow_property_count:
                        flow_property_count[fp.flow_property.name] = 0
                    flow_property_count[fp.flow_property.name] += 1
        for name, count in flow_property_count.items():
            print(f"{name}: {count}")

