from nlp_query_processor import OceanographicNLP

nlp_system = OceanographicNLP()

test_queries = [
    'depth of indian ocean in 2008',
    'temperature of indian ocean in 2008', 
    'salinity of pacific ocean',
    'pressure measurements in atlantic',
    'ocean temperature in july',
    'depth and temperature data'
]

print("Testing measurement type extraction:")
print("=" * 50)

for query in test_queries:
    intent = nlp_system.parse_query(query)
    measurements = [mt.value for mt in intent.measurement_types]
    print(f'Query: "{query}"')
    print(f'Measurements: {measurements}')
    print('-' * 30)