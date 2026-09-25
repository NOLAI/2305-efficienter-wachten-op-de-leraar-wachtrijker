from datasets import Dataset
from torch.utils.data import DataLoader
from transformers import DataCollatorWithPadding


def create_dataset(text, labels, tokenizer):
    if isinstance(text, str):
        text = [text]
    if labels is None:
        labels = [0] * len(text)

    # Create a Hugging Face Dataset. "category" duplicates the labels as a
    # class-encoded column purely so create_train_test_loader can stratify the
    # split on it; "label" stays float for the regression head.
    dataset = Dataset.from_dict({"text": text, "label": labels, "category": labels})
    dataset = dataset.class_encode_column("category")

    # Tokenize it
    def tokenize_function(examples):
        return tokenizer(examples["text"], padding=False, truncation=True)

    tokenized_dataset = dataset.map(tokenize_function, batched=True)

    return tokenized_dataset


def create_data_loader(text, labels, tokenizer, batch_size):
    dataset = create_dataset(text, labels, tokenizer)
    dataset.set_format(type="torch", columns=["input_ids", "attention_mask", "label"])

    data_collator = DataCollatorWithPadding(tokenizer=tokenizer)

    return DataLoader(dataset, batch_size=batch_size, collate_fn=data_collator)


def create_train_test_loader(text, labels, tokenizer, batch_size, seed=42):
    dataset = create_dataset(text, labels, tokenizer)
    dataset = dataset.train_test_split(test_size=0.2, stratify_by_column="category", shuffle=True, seed=seed)

    train_dataset = dataset["train"]
    train_dataset.set_format(type="torch", columns=["input_ids", "attention_mask", "label"])

    val_dataset = dataset["test"]
    val_dataset.set_format(type="torch", columns=["input_ids", "attention_mask", "label"])

    data_collator = DataCollatorWithPadding(tokenizer=tokenizer)

    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, collate_fn=data_collator)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, collate_fn=data_collator)

    return train_loader, val_loader
