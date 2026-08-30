from olx_location import resolve_olx_location


location = input("Enter location: ").strip()

result = resolve_olx_location(location)

print()
print("=" * 50)
print("RESULT")
print("=" * 50)
print(f"Input:  {location}")
print(f"OLX:    {result}")
