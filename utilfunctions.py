import logging, csv, contextlib, sys

logger = logging.getLogger(__name__)


def convert_query_response_to_list(response):
    listOut = []
    listOut.append(response['columns'])
    for row in response['rows']:
        listOut.append(row)
    return listOut


def write_list_to_csv(listIn, csvFilename):
    with open(csvFilename, 'wb') as csvFile:
        csvWriter = csv.writer(csvFile, delimiter=',')
        for row in listIn:
            csvWriter.writerow(row)


def load_csv_as_list(csvFilename):
    listOut = []
    with open(csvFilename, 'rb') as csvFile:
        csvReader = csv.reader(csvFile, delimiter=',')
        for row in csvReader:
            listOut.append(row)
    return listOut


@contextlib.contextmanager
def redirect_argv(temp_argv):
    _argv = sys.argv
    sys.argv = temp_argv
    yield
    sys.argv = _argv


class CursorIterator(object):
    def __init__(self, cursor):
        self.cursor = cursor
        self.cursor.reset()
    def next(self):
        n = self.cursor.next()
        if n is None:
            self.cursor.reset()
            raise StopIteration
        return n
    def __iter__(self):
        return self


def get_fieldnames(fields, ignorefields=[]):
    fields = CursorIterator(fields)
    fields_output = []
    for field in fields:
        if not field.name in ignorefields:
            fields_output.append(field.name)
    return fields_output