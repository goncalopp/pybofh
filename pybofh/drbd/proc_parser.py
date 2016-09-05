import itertools

attribute_names= {
    "cs":  "connection_state",
    "ro":  "roles",
    "ds":  "disk_states",
    "ns":  "network_send",
    "nr":  "network_receive",
    "dw":  "disk_write",
    "dr":  "disk_read",
    "al":  "activity_log",
    "bm":  "bit_map",
    "lo":  "local_count",
    "pe":  "pending",
    "ua":  "unacknowledged",
    "ap":  "application_pending",
    "ep":  "epochs",
    "wo":  "write_order",
    "oos": "out_of_sync",
    #--- only parser introduced attributes below
    "rp":  "replication_protocol",
    "iof": "io_flags"
}

def parse_proc_drbd(file_='/proc/drbd'):
    def is_resource_start_line(s):
        return s[0] == " " and s[1] != " "
    def tokenize_resource(lines):
        def is_kv_item(s):
            return ":" in s and s[-1] != ":" #title ends in :
        def parse_kv_item( s ):
            '''example:     cs:Connected'''
            try:
                k,v= s.split(":")
                try:
                    v= int(v)
                except ValueError:
                    pass
                return k,v
            except ValueError:
                raise Exception("Failed to parse token    "+s)
        tokens= list(itertools.chain(*map(str.split, lines)))
        #extract name
        tokens[0][-1]==":" # resource name/number
        #extract items
        kv_items={}
        non_kv_items=[]
        for token in tokens:
            if is_kv_item(token):
                k,v= parse_kv_item(token)
                kv_items[k]= v
            else:
                non_kv_items.append(token)
        return kv_items, non_kv_items
    def parse_resource(lines, version):
        kvs, nkvs= tokenize_resource(lines)
        #extract name
        name = nkvs.pop(0)
        assert name.endswith(":")
        name= name[:-1]
        #fill missing keys
        if version[:3] in ("8.3", "8.4"):
            assert len(kvs)==16
            assert len(nkvs)==2
            kvs['rp'], kvs['iof']= nkvs
            nkvs=[]
        return kvs, nkvs
    def parse_version(line):
        tokens= line.split()
        assert tokens[0] == "version:"
        version= tokens[1]
        assert "." in version
        return version
    try:
        lines= file_.read().splitlines()
    except AttributeError:
        lines= open(file_).read().splitlines()
    version= parse_version(lines[0])
    #lines[1] is the src version
    assert len(lines)==2 or is_resource_start_line(lines[2])
    resource_indexes= [i for i,line in enumerate(lines) if is_resource_start_line(line)]
    resource_indexes.append(len(lines))
    resource_lines= [lines[a:b] for a,b in zip(resource_indexes[:-1], resource_indexes[1:])]
    resources= [parse_resource(lines, version) for lines in resource_lines]
    return version, resources

