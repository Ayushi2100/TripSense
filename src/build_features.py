"""Run with:  python -m src.build_features   (from the TripSense folder)"""
from . import config, features, load


def main():
    config.PROC.mkdir(parents=True, exist_ok=True)
    tables = load.load_all()
    feats, months = features.build_all(tables)
    feats.to_csv(config.PROC / "destination_features.csv", index=False, encoding="utf-8")
    months.to_csv(config.PROC / "destination_month_features.csv", index=False, encoding="utf-8")
    features.interest_mapping_table().to_csv(config.PROC / "interest_mapping.csv", index=False, encoding="utf-8")
    features.feature_dictionary().to_csv(config.PROC / "feature_dictionary.csv", index=False, encoding="utf-8")
    features.season_sensitivity(tables["weather"]).to_csv(
        config.PROC / "season_rule_sensitivity.csv", encoding="utf-8")
    cols = [f"share_{i}" for i in config.INTERESTS]
    features.cosine_similarity_matrix(feats, cols).to_csv(
        config.PROC / "interest_similarity.csv", encoding="utf-8")
    print(f"Wrote {len(feats)} destinations x {feats.shape[1]} features and {len(months)} destination-months")


if __name__ == "__main__":
    main()
