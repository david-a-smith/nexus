from urllib.parse import urlparse
import simplejson as json
import os.path
import jsonpath_rw

cache = {}

SHARED_SCHEMA_PATH = os.path.realpath(os.path.dirname(os.path.realpath(__file__)) + '/../../schema')


class RefResolver:

    def __init__(self, identifier=None, schema_search_paths=[]):
        self.id = identifier
        if identifier is not None:
            self.url_fragments = urlparse(identifier)
        else:
            self.url_fragments = None

        self.schema_search_paths = schema_search_paths

        # always include the common schemas
        if SHARED_SCHEMA_PATH not in self.schema_search_paths:
            self.add_schema_path(SHARED_SCHEMA_PATH)

    def add_schema_path(self, path):
        self.schema_search_paths.append(path)

    def resolve_schema_path(self, file):
        for search_path in self.schema_search_paths:
            full_path = search_path + '/' + file
            if os.path.isfile(full_path):
                return full_path

    def resolve(self, json_obj):
        if isinstance(json_obj, dict):
            for key, value in json_obj.items():
                if key == "$ref":
                    ref_frag = urlparse(value)
                    ref_file = ref_frag.netloc + ref_frag.path

                    if ref_file in cache:
                        json_dump = cache[ref_file]
                    else:
                        resolved_path = self.resolve_schema_path(ref_file)
                        if resolved_path:
                            # if the ref is another file -> go there and get it
                            with open(resolved_path, 'r') as read_file:
                                json_dump = json.load(read_file)

                            ref_id = None
                            if 'id' in json_dump:
                                ref_id = json_dump['id']
                            cache[resolved_path] = json_dump
                            RefResolver(ref_id, schema_search_paths=self.schema_search_paths).resolve(json_dump)
                            cache[resolved_path] = json_dump
                        else:
                            # if the ref is in the same file grab it from the same file
                            json_dump = json.load(open(ref_frag.netloc+ref_frag.path))
                            cache[ref_file] = json_dump

                    ref_path_expr = "$" + ".".join(ref_frag.fragment.split("/"))
                    path_expression = jsonpath_rw.parse(ref_path_expr)
                    list_of_values = [match.value for match in path_expression.find(json_dump)]

                    if len(list_of_values) > 0:
                        resolution = list_of_values[0]
                        return resolution

                resolved = self.resolve(value)
                if resolved is not None:
                    json_obj[key] = resolved
        elif isinstance(json_obj, list):
            for (key, value) in enumerate(json_obj):
                resolved = self.resolve(value)
                if resolved is not None:
                    json_obj[key] = resolved
        return None
