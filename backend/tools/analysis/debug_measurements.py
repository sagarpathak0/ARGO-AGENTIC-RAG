from nlp_query_processor import OceanographicNLP

nlp_system = OceanographicNLP()

# Test with specific query
query = 'depth of indian ocean in 2008'
print(f'Testing query: "{query}"')
print()

# Debug measurement extraction
found_types = []
for measurement_type, keywords in nlp_system.measurement_keywords.items():
    print(f'Checking {measurement_type.value}: {keywords}')
    for keyword in keywords:
        if keyword in query:
            print(f'  ✓ Found keyword: "{keyword}"')
            if measurement_type not in found_types:
                found_types.append(measurement_type)
            break
    else:
        print(f'  ✗ No match')

print()
print(f'Final measurements found: {[mt.value for mt in found_types]}')

# Test the actual function
intent = nlp_system.parse_query(query)
print(f'NLP system result: {[mt.value for mt in intent.measurement_types]}')