from config import load_filters
from olx_url import build_olx_url


def main():
    filters = load_filters()

    print("=" * 60)
    print("OLX FILTER TEST")
    print("=" * 60)

    print("\nCurrent filters:")
    for key, value in filters.items():
        print(f"  {key}: {value}")

    url = build_olx_url(filters)

    print("\nGenerated OLX URL:")
    print(url)

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()