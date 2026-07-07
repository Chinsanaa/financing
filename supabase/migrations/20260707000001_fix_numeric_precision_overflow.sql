-- Fix numeric field overflow: cv_accuracy and f1_macro had impossible precision (3,4)
-- Changed to (5,4) to allow values like 0.9999

ALTER TABLE model_runs
  ALTER COLUMN cv_accuracy TYPE numeric(5, 4),
  ALTER COLUMN f1_macro TYPE numeric(5, 4);

-- Verify the fix works
-- SELECT cv_accuracy, f1_macro FROM model_runs LIMIT 1;
