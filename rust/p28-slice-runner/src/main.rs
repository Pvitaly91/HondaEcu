use std::io::{self, Read, Write};

use p28_slice_runner::{protocol::Request, runner::run_request};

// Bounded producer input vectors fit in one request/process, never one process per case.
const MAX_REQUEST_BYTES: u64 = 16 * 1_048_576;

fn main() {
    if let Err(error) = run() {
        eprintln!("runner request failed: {error}");
        std::process::exit(2);
    }
}

fn run() -> Result<(), Box<dyn std::error::Error>> {
    if std::env::args_os().len() != 1 {
        return Err("runner accepts one JSON request on stdin, no arguments".into());
    }
    let mut bytes = Vec::new();
    io::stdin()
        .take(MAX_REQUEST_BYTES + 1)
        .read_to_end(&mut bytes)?;
    if bytes.len() as u64 > MAX_REQUEST_BYTES {
        return Err("request exceeds size limit".into());
    }
    let request: Request = serde_json::from_slice(&bytes)?;
    let response = run_request(request)?;
    let stdout = io::stdout();
    let mut output = io::BufWriter::new(stdout.lock());
    serde_json::to_writer(&mut output, &response)?;
    output.write_all(b"\n")?;
    output.flush()?;
    Ok(())
}
