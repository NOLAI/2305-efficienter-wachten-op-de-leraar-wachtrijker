import logging

import torch
from torch.optim import AdamW
from transformers import get_linear_schedule_with_warmup

logger = logging.getLogger(__name__)


def train_model(train_loader, val_loader, model, tokenizer, output_dir, max_epochs=20, learning_rate=1e-5):
    logger.info("Starting model fine-tuning")

    logger.info(f"[Training]   Train size: {len(train_loader)}, Validation size: {len(val_loader)}")

    # Optimization function
    optimizer = AdamW(model.parameters(), lr=learning_rate)

    # Add gradual warmup to training
    num_training_steps = len(train_loader) * 5  # Pre-set to 5 epochs
    scheduler = get_linear_schedule_with_warmup(
        optimizer, num_warmup_steps=0.1 * num_training_steps, num_training_steps=num_training_steps
    )

    lowest_val_loss = None
    not_improved_since = 0
    for epoch in range(max_epochs):
        model.train()
        train_loss = 0
        mse = 0
        ss_res = 0
        ss_tot = 0
        for i, batch in enumerate(train_loader):
            batch = {k: v.to("cuda" if torch.cuda.is_available() else "cpu") for k, v in batch.items()}

            # Passing the data to the model
            outputs = model(**batch)

            # Calculating the gradient for the loss function
            loss = outputs.loss
            loss.backward()

            # Adjust with gradient clipping
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)

            # Optimizing the parameters of the bert model
            optimizer.step()
            optimizer.zero_grad()
            scheduler.step()

            # Calculating the running loss for logging purposes
            train_batch_loss = loss.item()
            train_loss += train_batch_loss * batch["input_ids"].size(0)

            # Calculating the MSE
            mse += torch.sum((batch["labels"] - outputs.logits.squeeze()) ** 2).item()

            # Calculating the R2
            ss_res += torch.sum((batch["labels"] - outputs.logits.squeeze()) ** 2)
            ss_tot += torch.sum((batch["labels"] - torch.mean(batch["labels"])) ** 2)

            logger.debug(f"[Training]    batch {i + 1}, loss: {train_batch_loss}")

        # Logging epoch-wise training loss
        logger.info(
            f"[Training]   epoch {epoch + 1}, loss: {train_loss / len(train_loader):.4f}, MSE: {mse / len(train_loader):.2f}, R2: {(1 - ss_res / ss_tot):.2f}"
        )

        model.eval()
        val_loss = 0
        mse = 0
        ss_res = 0
        ss_tot = 0
        for i, batch in enumerate(val_loader):
            batch = {k: v.to("cuda" if torch.cuda.is_available() else "cpu") for k, v in batch.items()}

            # We don't need gradients for testing
            with torch.no_grad():
                outputs = model(**batch)

            # Calculating the gradient for the loss function
            loss = outputs.loss

            # Calculating the running loss for logging purposes
            val_batch_loss = loss.item()
            val_loss += val_batch_loss * batch["input_ids"].size(0)

            # Calculating the MSE
            mse += torch.sum((batch["labels"] - outputs.logits.squeeze()) ** 2).item()

            # Calculating the R2
            ss_res += torch.sum((batch["labels"] - outputs.logits.squeeze()) ** 2)
            ss_tot += torch.sum((batch["labels"] - torch.mean(batch["labels"])) ** 2)

            logger.debug(f"[Validation] batch {i + 1}, loss: {val_batch_loss}")

        logger.info(
            f"[Validation] epoch {epoch + 1}, loss: {val_loss / len(val_loader):.4f}, MSE: {mse / len(val_loader):.2f}, R2: {(1 - ss_res / ss_tot):.2f}"
        )

        if lowest_val_loss is None:
            lowest_val_loss = val_loss
            model.save_pretrained(output_dir)
            tokenizer.save_pretrained(output_dir)
            logger.info(f"Saved epoch output to '{output_dir}'")
            continue
        elif val_loss + 0.0001 >= lowest_val_loss:
            not_improved_since += 1
            logger.info(f"Model did not improve enough for {not_improved_since} epochs")
            if not_improved_since >= 3:
                logger.info(f"Stopping training early at epoch {epoch + 1} as validation loss did not increase enough")
                break
        else:
            not_improved_since = 0
            model.save_pretrained(output_dir)
            tokenizer.save_pretrained(output_dir)
            logger.info(f"Saved epoch output to '{output_dir}'")
        lowest_val_loss = min(lowest_val_loss, val_loss)
