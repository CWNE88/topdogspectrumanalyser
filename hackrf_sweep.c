/*
 * Copyright 2016-2022 Great Scott Gadgets <info@greatscottgadgets.com>
 * Copyright 2016 Dominic Spill <dominicgs@gmail.com>
 * Copyright 2016 Mike Walters <mike@flomp.net>
 *
 * This file is part of HackRF.
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2, or (at your option)
 * any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; see the file COPYING.  If not, write to
 * the Free Software Foundation, Inc., 51 Franklin Street,
 * Boston, MA 02110-1301, USA.
 */

/* Must precede all system includes to take effect on glibc. */
#define _FILE_OFFSET_BITS 64

#include <hackrf.h>

#include <stdbool.h>
#include <stdatomic.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <getopt.h>
#include <time.h>
#include <float.h>

#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <errno.h>
#include <fftw3.h>
#include <inttypes.h>

#ifdef _WIN32
	#define _USE_MATH_DEFINES
	#include <windows.h>
	#include <io.h>
	#ifdef _MSC_VER

		#ifdef _WIN64
typedef int64_t ssize_t;
		#else
typedef int32_t ssize_t;
		#endif

		#define strtoull _strtoui64
		#define snprintf _snprintf

int gettimeofday(struct timeval* tv, void* ignored)
{
	FILETIME ft;
	unsigned __int64 tmp = 0;
	if (NULL != tv) {
		GetSystemTimeAsFileTime(&ft);
		tmp |= ft.dwHighDateTime;
		tmp <<= 32;
		tmp |= ft.dwLowDateTime;
		tmp /= 10;
		tmp -= 11644473600000000Ui64;
		tv->tv_sec = (long) (tmp / 1000000UL);
		tv->tv_usec = (long) (tmp % 1000000UL);
	}
	return 0;
}

	#endif
#endif

#if defined(__GNUC__)
	#include <unistd.h>
	#include <sys/time.h>
#endif

#include <signal.h>
#include <math.h>

/* 1 MiB output buffer — large enough to amortise syscall overhead at 40 MB/s. */
#define FD_BUFFER_SIZE (1 * 1024 * 1024)

#define FREQ_ONE_MHZ (1000000ull)

#define FREQ_MIN_MHZ (0)    /*    0 MHz */
#define FREQ_MAX_MHZ (7250) /* 7250 MHz */

#define DEFAULT_SAMPLE_RATE_HZ            (20000000) /* 20 MHz */
#define DEFAULT_BASEBAND_FILTER_BANDWIDTH (15000000) /* 15 MHz */

#define TUNE_STEP (DEFAULT_SAMPLE_RATE_HZ / FREQ_ONE_MHZ)
#define OFFSET    7500000

#define BLOCKS_PER_TRANSFER 16

/* Hardware gain limits */
#define LNA_GAIN_MAX 40
#define VGA_GAIN_MAX 62

/* Sync marker that opens every sweep block from the firmware */
#define SYNC_BYTE_0 0x7F
#define SYNC_BYTE_1 0x7F

/*
 * Interleaved-mode FFT bin geometry.
 * Each 20 MHz step yields two quarter-band sub-bands from an N-bin FFT:
 *   Lower sub-band: bins [1 + 5N/8 .. 1 + 5N/8 + N/4 - 1]
 *   Upper sub-band: bins [1 +  N/8 .. 1 +  N/8  + N/4 - 1]
 */
#define LOWER_BAND_OFFSET(n) (1 + ((n) * 5) / 8)
#define UPPER_BAND_OFFSET(n) (1 + (n) / 8)
#define BAND_BIN_COUNT(n)    ((n) / 4)

#define POLL_INTERVAL_MS 50
#define TIME_STR_LEN     50

/*
 * Calibration file format:
 *   6 × uint32_t header: magic, version, num_fft_bins, sample_rate_hz,
 *                        filter_bandwidth_hz, num_sweeps_averaged
 *   num_fft_bins × float32: per-bin dB correction values
 *
 * Correction is (mean_of_used_bins - measured_avg[bin]).  Adding it to every
 * pwr[bin] flattens the filter rolloff shape across the output spectrum.
 */
#define CAL_MAGIC          0x484B4346u  /* 'H','K','C','F' */
#define CAL_VERSION        1u
#define CAL_DEFAULT_SWEEPS 100u

#if defined _WIN32
	#define m_sleep(a) Sleep((a))
#else
	#define m_sleep(a) usleep((a) * 1000)
#endif

/* -------------------------------------------------------------------------
 * Context — all shared state between main() and the USB callback thread.
 * Kept as a file-scope struct so the signal handler can reach do_exit
 * without a separate global.
 * ---------------------------------------------------------------------- */
typedef struct {
	volatile sig_atomic_t do_exit;

	FILE*            outfile;
	_Atomic uint32_t byte_count;
	_Atomic uint64_t sweep_count;

	struct timeval usb_transfer_time;

	bool     timestamp_normalized;
	bool     binary_output;
	bool     ifft_output;
	bool     one_shot;
	bool     finite_mode;
	uint64_t num_sweeps;
	bool     sweep_started;

	int    num_fft_bins;
	double fft_bin_width;
	/* step_count is valid for IFFT mode only (num_ranges == 1 enforced). */
	int    step_count;

	uint16_t frequencies[MAX_SWEEP_RANGES * 2];
	int      num_ranges;

	fftwf_complex* fftwIn;
	fftwf_complex* fftwOut;
	fftwf_plan     fftwPlan;

	fftwf_complex* ifftwIn;
	fftwf_complex* ifftwOut;
	fftwf_plan     ifftwPlan;
	uint32_t       ifft_idx;

	float* pwr;
	float* window;

	/* Calibration (-C write, -c read) */
	bool        cal_mode;        /* accumulate noise floor, then write file */
	const char* cal_save_path;   /* -C: path to write correction file       */
	const char* cal_load_path;   /* -c: path to read correction file        */
	double*     cal_accum;       /* running sum of pwr[i] across all blocks */
	uint64_t    cal_block_count; /* number of FFT blocks accumulated        */
	float*      correction;      /* per-bin dB correction loaded from -c    */
} sweep_ctx_t;

static sweep_ctx_t ctx;

/* -------------------------------------------------------------------------
 * Utilities
 * ---------------------------------------------------------------------- */

static float TimevalDiff(const struct timeval* a, const struct timeval* b)
{
	return (a->tv_sec - b->tv_sec) + 1e-6f * (a->tv_usec - b->tv_usec);
}

int parse_u32(char* s, uint32_t* const value)
{
	uint_fast8_t base = 10;
	char* s_end;
	uint64_t ulong_value;

	if (strlen(s) > 2) {
		if (s[0] == '0') {
			if ((s[1] == 'x') || (s[1] == 'X')) {
				base = 16;
				s += 2;
			} else if ((s[1] == 'b') || (s[1] == 'B')) {
				base = 2;
				s += 2;
			}
		}
	}

	s_end = s;
	ulong_value = strtoul(s, &s_end, base);
	if ((s != s_end) && (*s_end == 0)) {
		*value = (uint32_t) ulong_value;
		return HACKRF_SUCCESS;
	} else {
		return HACKRF_ERROR_INVALID_PARAM;
	}
}

/* Works on a local copy — does not modify the caller's string. */
int parse_u32_range(const char* s, uint32_t* const value_min, uint32_t* const value_max)
{
	char buf[64];
	if (strlen(s) >= sizeof(buf)) {
		return HACKRF_ERROR_INVALID_PARAM;
	}
	strncpy(buf, s, sizeof(buf));
	buf[sizeof(buf) - 1] = '\0';

	char* sep = strchr(buf, ':');
	if (!sep) {
		return HACKRF_ERROR_INVALID_PARAM;
	}
	*sep = '\0';

	int result = parse_u32(buf, value_min);
	if (result != HACKRF_SUCCESS) {
		return result;
	}
	return parse_u32(sep + 1, value_max);
}

/* Returns dBFS for one complex FFT bin.  Returns -FLT_MAX for a zero bin
 * rather than propagating -infinity into the output. */
static float logPower(fftwf_complex in, float scale)
{
	float re    = in[0] * scale;
	float im    = in[1] * scale;
	float magsq = re * re + im * im;
	if (magsq == 0.0f) {
		return -FLT_MAX;
	}
	return 10.0f * log10f(magsq);
}

/* -------------------------------------------------------------------------
 * rx_callback helpers
 * ---------------------------------------------------------------------- */

static void flush_ifft(sweep_ctx_t* c)
{
	int   ifft_bins = c->num_fft_bins * c->step_count;
	float norm      = 1.0f / (float) ifft_bins;

	fftwf_execute(c->ifftwPlan);
	for (int i = 0; i < ifft_bins; i++) {
		c->ifftwOut[i][0] *= norm;
		c->ifftwOut[i][1] *= norm;
		fwrite(&c->ifftwOut[i][0], sizeof(float), 1, c->outfile);
		fwrite(&c->ifftwOut[i][1], sizeof(float), 1, c->outfile);
	}
}

static void write_binary_record(sweep_ctx_t* c, uint64_t frequency)
{
	int      n             = c->num_fft_bins;
	uint32_t record_length = 2 * sizeof(uint64_t) +
		(uint32_t) BAND_BIN_COUNT(n) * sizeof(float);
	uint64_t band_edge;

	/* Lower sub-band */
	fwrite(&record_length, sizeof(record_length), 1, c->outfile);
	band_edge = frequency;
	fwrite(&band_edge, sizeof(band_edge), 1, c->outfile);
	band_edge = frequency + DEFAULT_SAMPLE_RATE_HZ / 4;
	fwrite(&band_edge, sizeof(band_edge), 1, c->outfile);
	fwrite(&c->pwr[LOWER_BAND_OFFSET(n)], sizeof(float),
	       BAND_BIN_COUNT(n), c->outfile);

	/* Upper sub-band */
	fwrite(&record_length, sizeof(record_length), 1, c->outfile);
	band_edge = frequency + DEFAULT_SAMPLE_RATE_HZ / 2;
	fwrite(&band_edge, sizeof(band_edge), 1, c->outfile);
	band_edge = frequency + (DEFAULT_SAMPLE_RATE_HZ * 3) / 4;
	fwrite(&band_edge, sizeof(band_edge), 1, c->outfile);
	fwrite(&c->pwr[UPPER_BAND_OFFSET(n)], sizeof(float),
	       BAND_BIN_COUNT(n), c->outfile);
}

static void write_text_record(sweep_ctx_t* c, uint64_t frequency)
{
	int        n                  = c->num_fft_bins;
	time_t     time_stamp_seconds = c->usb_transfer_time.tv_sec;
	struct tm* fft_time           = localtime(&time_stamp_seconds);
	char       time_str[TIME_STR_LEN];

	strftime(time_str, sizeof(time_str), "%Y-%m-%d, %H:%M:%S", fft_time);

	/* Lower sub-band */
	fprintf(c->outfile,
		"%s.%06ld, %" PRIu64 ", %" PRIu64 ", %.2f, %u",
		time_str,
		(long int) c->usb_transfer_time.tv_usec,
		frequency,
		frequency + DEFAULT_SAMPLE_RATE_HZ / 4,
		c->fft_bin_width,
		(unsigned int) n);
	for (int i = 0; i < BAND_BIN_COUNT(n); i++) {
		fprintf(c->outfile, ", %.2f", c->pwr[LOWER_BAND_OFFSET(n) + i]);
	}
	fprintf(c->outfile, "\n");

	/* Upper sub-band */
	fprintf(c->outfile,
		"%s.%06ld, %" PRIu64 ", %" PRIu64 ", %.2f, %u",
		time_str,
		(long int) c->usb_transfer_time.tv_usec,
		frequency + DEFAULT_SAMPLE_RATE_HZ / 2,
		frequency + (DEFAULT_SAMPLE_RATE_HZ * 3) / 4,
		c->fft_bin_width,
		(unsigned int) n);
	for (int i = 0; i < BAND_BIN_COUNT(n); i++) {
		fprintf(c->outfile, ", %.2f", c->pwr[UPPER_BAND_OFFSET(n) + i]);
	}
	fprintf(c->outfile, "\n");
}

static void accumulate_ifft(sweep_ctx_t* c, uint64_t frequency)
{
	int n         = c->num_fft_bins;
	int ifft_bins = n * c->step_count;

	c->ifft_idx = (uint32_t) round(
		(frequency - (uint64_t) (FREQ_ONE_MHZ * c->frequencies[0])) /
		c->fft_bin_width);
	c->ifft_idx = (c->ifft_idx + ifft_bins / 2) % ifft_bins;

	for (int i = 0; i < BAND_BIN_COUNT(n); i++) {
		c->ifftwIn[c->ifft_idx + i][0] = c->fftwOut[LOWER_BAND_OFFSET(n) + i][0];
		c->ifftwIn[c->ifft_idx + i][1] = c->fftwOut[LOWER_BAND_OFFSET(n) + i][1];
	}
	c->ifft_idx = (c->ifft_idx + n / 2) % ifft_bins;
	for (int i = 0; i < BAND_BIN_COUNT(n); i++) {
		c->ifftwIn[c->ifft_idx + i][0] = c->fftwOut[UPPER_BAND_OFFSET(n) + i][0];
		c->ifftwIn[c->ifft_idx + i][1] = c->fftwOut[UPPER_BAND_OFFSET(n) + i][1];
	}
}

/* -------------------------------------------------------------------------
 * Calibration — save and load correction files
 * ---------------------------------------------------------------------- */

static int save_calibration(sweep_ctx_t* c)
{
	if (c->cal_block_count == 0) {
		fprintf(stderr, "No calibration data accumulated.\n");
		return 0;
	}

	int     n   = c->num_fft_bins;
	float*  avg = malloc((size_t) n * sizeof(float));
	if (!avg) {
		fprintf(stderr, "Out of memory saving calibration.\n");
		return 0;
	}

	for (int i = 0; i < n; i++) {
		avg[i] = (float) (c->cal_accum[i] / (double) c->cal_block_count);
	}

	/* Compute reference level from used bins only — DC and edge-rolloff bins
	 * have garbage values and must not skew the mean. */
	double mean = 0.0;
	int    used = 0;
	for (int i = 0; i < n; i++) {
		bool in_lower = (i >= LOWER_BAND_OFFSET(n) &&
		                 i <  LOWER_BAND_OFFSET(n) + BAND_BIN_COUNT(n));
		bool in_upper = (i >= UPPER_BAND_OFFSET(n) &&
		                 i <  UPPER_BAND_OFFSET(n) + BAND_BIN_COUNT(n));
		if ((in_lower || in_upper) && avg[i] > -FLT_MAX) {
			mean += avg[i];
			used++;
		}
	}
	if (used == 0) {
		fprintf(stderr, "No valid calibration bins.\n");
		free(avg);
		return 0;
	}
	mean /= used;

	/* correction[i] = mean - avg[i] for used bins, 0 for unused bins. */
	float* correction = calloc((size_t) n, sizeof(float));
	if (!correction) {
		fprintf(stderr, "Out of memory saving calibration.\n");
		free(avg);
		return 0;
	}
	for (int i = 0; i < n; i++) {
		bool in_lower = (i >= LOWER_BAND_OFFSET(n) &&
		                 i <  LOWER_BAND_OFFSET(n) + BAND_BIN_COUNT(n));
		bool in_upper = (i >= UPPER_BAND_OFFSET(n) &&
		                 i <  UPPER_BAND_OFFSET(n) + BAND_BIN_COUNT(n));
		if (in_lower || in_upper) {
			correction[i] = (float) (mean - avg[i]);
		}
	}

	FILE* f = fopen(c->cal_save_path, "wb");
	if (!f) {
		fprintf(stderr, "Cannot write calibration file: %s\n", c->cal_save_path);
		free(avg);
		free(correction);
		return 0;
	}

	uint32_t header[6] = {
		CAL_MAGIC,
		CAL_VERSION,
		(uint32_t) n,
		DEFAULT_SAMPLE_RATE_HZ,
		DEFAULT_BASEBAND_FILTER_BANDWIDTH,
		(uint32_t) atomic_load(&c->sweep_count),
	};
	fwrite(header,     sizeof(uint32_t), 6, f);
	fwrite(correction, sizeof(float),    n, f);
	fclose(f);

	fprintf(stderr,
		"Calibration saved: %s  (%" PRIu64 " sweeps, %d bins, %.1f dB mean)\n",
		c->cal_save_path, atomic_load(&c->sweep_count), n, (float) mean);

	free(avg);
	free(correction);
	return 1;
}

static int load_calibration(sweep_ctx_t* c)
{
	FILE* f = fopen(c->cal_load_path, "rb");
	if (!f) {
		fprintf(stderr, "Cannot open calibration file: %s\n", c->cal_load_path);
		return 0;
	}

	uint32_t header[6];
	if (fread(header, sizeof(uint32_t), 6, f) != 6) {
		fprintf(stderr, "Calibration file too short: %s\n", c->cal_load_path);
		fclose(f);
		return 0;
	}

	if (header[0] != CAL_MAGIC) {
		fprintf(stderr, "Not a valid calibration file: %s\n", c->cal_load_path);
		fclose(f);
		return 0;
	}
	if (header[1] != CAL_VERSION) {
		fprintf(stderr,
			"Unsupported calibration file version %u\n", header[1]);
		fclose(f);
		return 0;
	}
	if ((int) header[2] != c->num_fft_bins) {
		fprintf(stderr,
			"Calibration bin count mismatch: "
			"file has %u bins, current -w setting gives %d bins\n",
			header[2], c->num_fft_bins);
		fclose(f);
		return 0;
	}
	if (header[3] != DEFAULT_SAMPLE_RATE_HZ) {
		fprintf(stderr, "Calibration sample rate mismatch.\n");
		fclose(f);
		return 0;
	}

	c->correction = malloc((size_t) c->num_fft_bins * sizeof(float));
	if (!c->correction) {
		fprintf(stderr, "Out of memory loading calibration.\n");
		fclose(f);
		return 0;
	}

	if (fread(c->correction, sizeof(float), c->num_fft_bins, f) !=
	        (size_t) c->num_fft_bins) {
		fprintf(stderr, "Calibration file truncated: %s\n", c->cal_load_path);
		free(c->correction);
		c->correction = NULL;
		fclose(f);
		return 0;
	}

	fclose(f);
	fprintf(stderr,
		"Calibration loaded: %s  (%u sweeps, %d bins)\n",
		c->cal_load_path, header[5], c->num_fft_bins);
	return 1;
}

/* -------------------------------------------------------------------------
 * USB transfer callback — called from the HackRF USB thread.
 * ---------------------------------------------------------------------- */
int rx_callback(hackrf_transfer* transfer)
{
	sweep_ctx_t* c = (sweep_ctx_t*) transfer->rx_ctx;

	if (!c->cal_mode && c->outfile == NULL) {
		return -1;
	}
	if (c->do_exit) {
		return 0;
	}

	if ((c->usb_transfer_time.tv_sec == 0 && c->usb_transfer_time.tv_usec == 0) ||
	    !c->timestamp_normalized) {
		gettimeofday(&c->usb_transfer_time, NULL);
	}

	atomic_fetch_add(&c->byte_count, (uint32_t) transfer->valid_length);

	int8_t* buf = (int8_t*) transfer->buffer;

	for (int j = 0; j < BLOCKS_PER_TRANSFER; j++) {
		uint8_t* ubuf = (uint8_t*) buf;

		if (ubuf[0] != SYNC_BYTE_0 || ubuf[1] != SYNC_BYTE_1) {
			buf += BYTES_PER_BLOCK;
			continue;
		}

		uint64_t frequency =
			((uint64_t) ubuf[9] << 56) | ((uint64_t) ubuf[8] << 48) |
			((uint64_t) ubuf[7] << 40) | ((uint64_t) ubuf[6] << 32) |
			((uint64_t) ubuf[5] << 24) | ((uint64_t) ubuf[4] << 16) |
			((uint64_t) ubuf[3] << 8)  |  (uint64_t) ubuf[2];

		if (frequency == (uint64_t) (FREQ_ONE_MHZ * c->frequencies[0])) {
			if (c->sweep_started) {
				if (c->ifft_output) {
					flush_ifft(c);
				}
				atomic_fetch_add(&c->sweep_count, 1ULL);

				if (c->timestamp_normalized) {
					gettimeofday(&c->usb_transfer_time, NULL);
				}

				if (c->one_shot ||
				    (c->finite_mode &&
				     atomic_load(&c->sweep_count) >= c->num_sweeps)) {
					c->do_exit = 1;
				}
			}
			c->sweep_started = true;
		}

		if (c->do_exit) {
			return 0;
		}
		if (!c->sweep_started) {
			buf += BYTES_PER_BLOCK;
			continue;
		}
		if (frequency > (uint64_t) (FREQ_MAX_MHZ * FREQ_ONE_MHZ)) {
			buf += BYTES_PER_BLOCK;
			continue;
		}

		buf += BYTES_PER_BLOCK - (c->num_fft_bins * 2);
		for (int i = 0; i < c->num_fft_bins; i++) {
			c->fftwIn[i][0] = buf[i * 2]     * c->window[i] * (1.0f / 128.0f);
			c->fftwIn[i][1] = buf[i * 2 + 1] * c->window[i] * (1.0f / 128.0f);
		}
		buf += c->num_fft_bins * 2;

		fftwf_execute(c->fftwPlan);

		float fft_scale = 1.0f / c->num_fft_bins;
		for (int i = 0; i < c->num_fft_bins; i++) {
			c->pwr[i] = logPower(c->fftwOut[i], fft_scale);
		}

		/* Apply loaded correction before output. */
		if (c->correction) {
			for (int i = 0; i < c->num_fft_bins; i++) {
				c->pwr[i] += c->correction[i];
			}
		}

		if (c->cal_mode) {
			/* Accumulate raw (uncorrected) noise floor for calibration.
			 * Correction is intentionally not applied here — we are
			 * measuring the filter shape itself. */
			for (int i = 0; i < c->num_fft_bins; i++) {
				c->cal_accum[i] += c->pwr[i];
			}
			c->cal_block_count++;
		} else if (c->binary_output) {
			write_binary_record(c, frequency);
		} else if (c->ifft_output) {
			accumulate_ifft(c, frequency);
		} else {
			write_text_record(c, frequency);
		}
	}
	return 0;
}

/* -------------------------------------------------------------------------
 * CLI / signal handling
 * ---------------------------------------------------------------------- */

static void usage(void)
{
	fprintf(stderr,
		"Usage:\n"
		"\t[-h] # this help\n"
		"\t[-d serial_number] # Serial number of desired HackRF\n"
		"\t[-a amp_enable] # RX RF amplifier 1=Enable, 0=Disable\n"
		"\t[-f freq_min:freq_max] # minimum and maximum frequencies in MHz\n"
		"\t[-p antenna_enable] # Antenna port power, 1=Enable, 0=Disable\n"
		"\t[-l gain_db] # RX LNA (IF) gain, 0-40dB, 8dB steps\n"
		"\t[-g gain_db] # RX VGA (baseband) gain, 0-62dB, 2dB steps\n"
		"\t[-w bin_width] # FFT bin width (frequency resolution) in Hz, 2445-5000000\n"
		"\t[-W wisdom_file] # Use FFTW wisdom file (will be created if necessary)\n"
		"\t[-P estimate|measure|patient|exhaustive] # FFTW plan type, default is 'measure'\n"
		"\t[-1] # one shot mode\n"
		"\t[-N num_sweeps] # Number of sweeps to perform\n"
		"\t[-B] # binary output\n"
		"\t[-I] # binary inverse FFT output\n"
		"\t[-n] # keep the same timestamp within a sweep\n"
		"\t[-C cal_file] # calibration mode: measure noise floor, write correction file\n"
		"\t[-c cal_file] # apply correction file to flatten filter rolloff\n"
		"\t-r filename # output file\n"
		"\n"
		"Calibration workflow:\n"
		"\t1. Disconnect antenna (or fit 50-ohm terminator)\n"
		"\t2. hackrf_sweep -f <range> -w <bin_width> -C my.hkcf\n"
		"\t   (use -N to set sweep count; default is 100)\n"
		"\t3. hackrf_sweep -f <range> -w <bin_width> -c my.hkcf -r out.bin\n"
		"\t   The same -w value must be used for calibration and normal use.\n"
		"\n"
		"Output fields:\n"
		"\tdate, time, hz_low, hz_high, hz_bin_width, num_samples, dB, dB, . . .\n");
}

static hackrf_device* device = NULL;

#ifdef _MSC_VER
BOOL WINAPI sighandler(int signum)
{
	if (CTRL_C_EVENT == signum || CTRL_BREAK_EVENT == signum) {
		fprintf(stderr, "Caught signal %d\n", signum);
		ctx.do_exit = 1;
		return TRUE;
	}
	return FALSE;
}
#else
static void sigint_callback_handler(int signum)
{
	(void) signum;
	ctx.do_exit = 1;
}
#endif

static int import_wisdom(const char* path)
{
	if (!fftwf_import_wisdom_from_filename(path)) {
		fprintf(stderr,
			"Wisdom file %s not found; will attempt to create it\n",
			path);
		return 0;
	}
	return 1;
}

static int import_default_wisdom(void)
{
	return fftwf_import_system_wisdom();
}

static int export_wisdom(const char* path)
{
	if (path != NULL) {
		if (!fftwf_export_wisdom_to_filename(path)) {
			fprintf(stderr, "Could not write FFTW wisdom file to %s\n", path);
			return 0;
		}
	}
	return 1;
}

static void free_fftw(sweep_ctx_t* c)
{
	if (c->fftwPlan)  { fftwf_destroy_plan(c->fftwPlan);  c->fftwPlan  = NULL; }
	if (c->ifftwPlan) { fftwf_destroy_plan(c->ifftwPlan); c->ifftwPlan = NULL; }
	fftwf_free(c->fftwIn);   c->fftwIn   = NULL;
	fftwf_free(c->fftwOut);  c->fftwOut  = NULL;
	fftwf_free(c->pwr);      c->pwr      = NULL;
	fftwf_free(c->window);   c->window   = NULL;
	fftwf_free(c->ifftwIn);  c->ifftwIn  = NULL;
	fftwf_free(c->ifftwOut); c->ifftwOut = NULL;
	free(c->cal_accum);      c->cal_accum   = NULL;
	free(c->correction);     c->correction  = NULL;
}

int main(int argc, char** argv)
{
	int opt, i, result = 0;
	const char* path          = NULL;
	const char* serial_number = NULL;
	int         exit_code     = EXIT_SUCCESS;
	struct timeval time_now;
	struct timeval time_prev;
	struct timeval t_start;
	float    time_diff;
	float    sweep_rate = 0;
	unsigned int lna_gain = 16, vga_gain = 20;
	uint32_t freq_min = 0;
	uint32_t freq_max = 6000;
	uint32_t requested_fft_bin_width;
	const char* fftwWisdomPath = NULL;
	int fftw_plan_type = FFTW_MEASURE;
	bool     amp    = false;
	uint32_t amp_enable = 0;
	bool     antenna = false;
	uint32_t antenna_enable = 0;

	memset(&ctx, 0, sizeof(ctx));
	atomic_init(&ctx.byte_count, 0);
	atomic_init(&ctx.sweep_count, 0);
	ctx.num_fft_bins = 20;

	while ((opt = getopt(argc, argv, "a:f:p:l:g:d:N:w:W:P:n1BIr:C:c:h?")) != EOF) {
		result = HACKRF_SUCCESS;
		switch (opt) {
		case 'd':
			serial_number = optarg;
			break;

		case 'a':
			amp    = true;
			result = parse_u32(optarg, &amp_enable);
			break;

		case 'f':
			result = parse_u32_range(optarg, &freq_min, &freq_max);
			if (result != HACKRF_SUCCESS) {
				break;
			}
			if (freq_min >= freq_max) {
				fprintf(stderr,
					"argument error: freq_max must be greater than freq_min.\n");
				usage();
				return EXIT_FAILURE;
			}
			if (FREQ_MAX_MHZ < freq_max) {
				fprintf(stderr,
					"argument error: freq_max may not be higher than %u.\n",
					FREQ_MAX_MHZ);
				usage();
				return EXIT_FAILURE;
			}
			if (MAX_SWEEP_RANGES <= ctx.num_ranges) {
				fprintf(stderr,
					"argument error: specify a maximum of %u frequency ranges.\n",
					MAX_SWEEP_RANGES);
				usage();
				return EXIT_FAILURE;
			}
			ctx.frequencies[2 * ctx.num_ranges]     = (uint16_t) freq_min;
			ctx.frequencies[2 * ctx.num_ranges + 1] = (uint16_t) freq_max;
			ctx.num_ranges++;
			break;

		case 'p':
			antenna = true;
			result  = parse_u32(optarg, &antenna_enable);
			break;

		case 'l':
			result = parse_u32(optarg, &lna_gain);
			break;

		case 'g':
			result = parse_u32(optarg, &vga_gain);
			break;

		case 'N': {
			ctx.finite_mode = true;
			uint32_t ns;
			result = parse_u32(optarg, &ns);
			ctx.num_sweeps = ns;
			break;
		}

		case 'w':
			result = parse_u32(optarg, &requested_fft_bin_width);
			ctx.num_fft_bins = DEFAULT_SAMPLE_RATE_HZ / requested_fft_bin_width;
			break;

		case 'W':
			fftwWisdomPath = optarg;
			break;

		case 'P':
			if (strcmp("estimate", optarg) == 0) {
				fftw_plan_type = FFTW_ESTIMATE;
			} else if (strcmp("measure", optarg) == 0) {
				fftw_plan_type = FFTW_MEASURE;
			} else if (strcmp("patient", optarg) == 0) {
				fftw_plan_type = FFTW_PATIENT;
			} else if (strcmp("exhaustive", optarg) == 0) {
				fftw_plan_type = FFTW_EXHAUSTIVE;
			} else {
				fprintf(stderr, "Unknown FFTW plan type '%s'\n", optarg);
				return EXIT_FAILURE;
			}
			break;

		case 'n':
			ctx.timestamp_normalized = true;
			break;

		case '1':
			ctx.one_shot = true;
			break;

		case 'B':
			ctx.binary_output = true;
			break;

		case 'I':
			ctx.ifft_output = true;
			break;

		case 'r':
			path = optarg;
			break;

		case 'C':
			ctx.cal_mode      = true;
			ctx.cal_save_path = optarg;
			break;

		case 'c':
			ctx.cal_load_path = optarg;
			break;

		case 'h':
		case '?':
			usage();
			return EXIT_SUCCESS;

		default:
			fprintf(stderr, "unknown argument '-%c %s'\n", opt, optarg);
			usage();
			return EXIT_FAILURE;
		}

		if (result != HACKRF_SUCCESS) {
			fprintf(stderr,
				"argument error: '-%c %s' %s (%d)\n",
				opt,
				optarg,
				hackrf_error_name(result),
				result);
			usage();
			return EXIT_FAILURE;
		}
	}

	if (ctx.cal_mode && ctx.cal_load_path) {
		fprintf(stderr,
			"argument error: -C (calibrate) and -c (apply) are mutually exclusive.\n");
		return EXIT_FAILURE;
	}

	if (fftwWisdomPath) {
		import_wisdom(fftwWisdomPath);
	} else {
		import_default_wisdom();
	}

	if (lna_gain % 8) {
		fprintf(stderr, "warning: lna_gain (-l) must be a multiple of 8\n");
	}
	if (lna_gain > LNA_GAIN_MAX) {
		fprintf(stderr,
			"argument error: lna_gain (-l) must be 0-%u dB\n",
			LNA_GAIN_MAX);
		return EXIT_FAILURE;
	}

	if (vga_gain % 2) {
		fprintf(stderr, "warning: vga_gain (-g) must be a multiple of 2\n");
	}
	if (vga_gain > VGA_GAIN_MAX) {
		fprintf(stderr,
			"argument error: vga_gain (-g) must be 0-%u dB\n",
			VGA_GAIN_MAX);
		return EXIT_FAILURE;
	}

	if (amp && amp_enable > 1) {
		fprintf(stderr, "argument error: amp_enable shall be 0 or 1.\n");
		usage();
		return EXIT_FAILURE;
	}

	if (antenna && antenna_enable > 1) {
		fprintf(stderr, "argument error: antenna_enable shall be 0 or 1.\n");
		usage();
		return EXIT_FAILURE;
	}

	if (0 == ctx.num_ranges) {
		ctx.frequencies[0] = (uint16_t) freq_min;
		ctx.frequencies[1] = (uint16_t) freq_max;
		ctx.num_ranges     = 1;
	}

	if (ctx.binary_output && ctx.ifft_output) {
		fprintf(stderr,
			"argument error: binary output (-B) and IFFT output (-I) are mutually exclusive.\n");
		return EXIT_FAILURE;
	}

	if (ctx.ifft_output && (1 < ctx.num_ranges)) {
		fprintf(stderr,
			"argument error: only one frequency range is supported in IFFT output (-I) mode.\n");
		return EXIT_FAILURE;
	}

	if (4 > ctx.num_fft_bins) {
		fprintf(stderr,
			"argument error: FFT bin width (-w) must be no more than 5000000\n");
		return EXIT_FAILURE;
	}

	if (8180 < ctx.num_fft_bins) {
		fprintf(stderr,
			"argument error: FFT bin width (-w) must be no less than 2445\n");
		return EXIT_FAILURE;
	}

	/* Round up to the nearest odd multiple of 4 for optimal interleaved bin selection. */
	while ((ctx.num_fft_bins + 4) % 8) {
		ctx.num_fft_bins++;
	}

	ctx.fft_bin_width = (double) DEFAULT_SAMPLE_RATE_HZ / ctx.num_fft_bins;

	ctx.fftwIn  = (fftwf_complex*) fftwf_malloc(sizeof(fftwf_complex) * ctx.num_fft_bins);
	ctx.fftwOut = (fftwf_complex*) fftwf_malloc(sizeof(fftwf_complex) * ctx.num_fft_bins);
	ctx.fftwPlan = fftwf_plan_dft_1d(
		ctx.num_fft_bins,
		ctx.fftwIn,
		ctx.fftwOut,
		FFTW_FORWARD,
		fftw_plan_type);
	ctx.pwr    = (float*) fftwf_malloc(sizeof(float) * ctx.num_fft_bins);
	ctx.window = (float*) fftwf_malloc(sizeof(float) * ctx.num_fft_bins);
	for (i = 0; i < ctx.num_fft_bins; i++) {
		ctx.window[i] = 0.5f *
			(1.0f - cosf(2.0f * (float) M_PI * i / (ctx.num_fft_bins - 1)));
	}

	/* Warm up the plan before real data arrives.  See issue #1366. */
	fftwf_execute(ctx.fftwPlan);

	memset(&ctx.usb_transfer_time, 0, sizeof(ctx.usb_transfer_time));

	/* Calibration setup — must happen after num_fft_bins is finalised. */
	if (ctx.cal_mode) {
		if (!ctx.finite_mode) {
			ctx.finite_mode = true;
			ctx.num_sweeps  = CAL_DEFAULT_SWEEPS;
		}
		ctx.cal_accum = calloc((size_t) ctx.num_fft_bins, sizeof(double));
		if (!ctx.cal_accum) {
			fprintf(stderr, "Out of memory for calibration buffer.\n");
			free_fftw(&ctx);
			return EXIT_FAILURE;
		}
		fprintf(stderr,
			"Calibration mode: accumulating %" PRIu64 " sweeps into %s\n"
			"  Disconnect antenna or fit 50-ohm terminator for best results.\n",
			ctx.num_sweeps, ctx.cal_save_path);
	}

	if (ctx.cal_load_path) {
		if (!load_calibration(&ctx)) {
			free_fftw(&ctx);
			return EXIT_FAILURE;
		}
	}

#ifdef _MSC_VER
	if (ctx.binary_output) {
		_setmode(_fileno(stdout), _O_BINARY);
	}
#endif

	result = hackrf_init();
	if (result != HACKRF_SUCCESS) {
		fprintf(stderr,
			"hackrf_init() failed: %s (%d)\n",
			hackrf_error_name(result),
			result);
		free_fftw(&ctx);
		usage();
		return EXIT_FAILURE;
	}

	result = hackrf_open_by_serial(serial_number, &device);
	if (result != HACKRF_SUCCESS) {
		fprintf(stderr,
			"hackrf_open() failed: %s (%d)\n",
			hackrf_error_name(result),
			result);
		free_fftw(&ctx);
		usage();
		return EXIT_FAILURE;
	}

	/* In calibration mode no output file is written; outfile must still be
	 * non-NULL to pass the rx_callback guard. */
	if (ctx.cal_mode) {
		ctx.outfile = stdout;
	} else if ((NULL == path) || (strcmp(path, "-") == 0)) {
		ctx.outfile = stdout;
	} else {
		ctx.outfile = fopen(path, "wb");
		if (NULL == ctx.outfile) {
			fprintf(stderr, "Failed to open file: %s\n", path);
			free_fftw(&ctx);
			return EXIT_FAILURE;
		}
		result = setvbuf(ctx.outfile, NULL, _IOFBF, FD_BUFFER_SIZE);
		if (result != 0) {
			fprintf(stderr, "setvbuf() failed: %d\n", result);
			free_fftw(&ctx);
			usage();
			return EXIT_FAILURE;
		}
	}

#ifdef _MSC_VER
	SetConsoleCtrlHandler((PHANDLER_ROUTINE) sighandler, TRUE);
#else
	/* Only catch graceful-exit signals.  SIGILL/SIGFPE/SIGSEGV/SIGABRT are
	 * process-fatal; returning from their handlers is undefined behaviour. */
	signal(SIGINT,  sigint_callback_handler);
	signal(SIGTERM, sigint_callback_handler);
#endif

	fprintf(stderr,
		"call hackrf_sample_rate_set(%.03f MHz)\n",
		((float) DEFAULT_SAMPLE_RATE_HZ / (float) FREQ_ONE_MHZ));
	result = hackrf_set_sample_rate_manual(device, DEFAULT_SAMPLE_RATE_HZ, 1);
	if (result != HACKRF_SUCCESS) {
		fprintf(stderr,
			"hackrf_sample_rate_set() failed: %s (%d)\n",
			hackrf_error_name(result),
			result);
		free_fftw(&ctx);
		usage();
		return EXIT_FAILURE;
	}

	fprintf(stderr,
		"call hackrf_baseband_filter_bandwidth_set(%.03f MHz)\n",
		((float) DEFAULT_BASEBAND_FILTER_BANDWIDTH / (float) FREQ_ONE_MHZ));
	result = hackrf_set_baseband_filter_bandwidth(
		device,
		DEFAULT_BASEBAND_FILTER_BANDWIDTH);
	if (result != HACKRF_SUCCESS) {
		fprintf(stderr,
			"hackrf_baseband_filter_bandwidth_set() failed: %s (%d)\n",
			hackrf_error_name(result),
			result);
		free_fftw(&ctx);
		usage();
		return EXIT_FAILURE;
	}

	result = hackrf_set_vga_gain(device, vga_gain);
	if (result != HACKRF_SUCCESS) {
		fprintf(stderr,
			"hackrf_set_vga_gain() failed: %s (%d)\n",
			hackrf_error_name(result),
			result);
		free_fftw(&ctx);
		return EXIT_FAILURE;
	}

	result = hackrf_set_lna_gain(device, lna_gain);
	if (result != HACKRF_SUCCESS) {
		fprintf(stderr,
			"hackrf_set_lna_gain() failed: %s (%d)\n",
			hackrf_error_name(result),
			result);
		free_fftw(&ctx);
		return EXIT_FAILURE;
	}

	for (i = 0; i < ctx.num_ranges; i++) {
		ctx.step_count =
			1 + (ctx.frequencies[2 * i + 1] - ctx.frequencies[2 * i] - 1) /
			TUNE_STEP;
		ctx.frequencies[2 * i + 1] =
			(uint16_t) (ctx.frequencies[2 * i] + ctx.step_count * TUNE_STEP);
		fprintf(stderr,
			"Sweeping from %u MHz to %u MHz\n",
			ctx.frequencies[2 * i],
			ctx.frequencies[2 * i + 1]);
	}

	if (ctx.ifft_output) {
		/* IFFT mode requires num_ranges == 1 (enforced above), so
		 * step_count holds the correct single-range value here. */
		int ifft_bins = ctx.num_fft_bins * ctx.step_count;
		ctx.ifftwIn  = (fftwf_complex*) fftwf_malloc(
			sizeof(fftwf_complex) * ifft_bins);
		ctx.ifftwOut = (fftwf_complex*) fftwf_malloc(
			sizeof(fftwf_complex) * ifft_bins);
		ctx.ifftwPlan = fftwf_plan_dft_1d(
			ifft_bins,
			ctx.ifftwIn,
			ctx.ifftwOut,
			FFTW_BACKWARD,
			fftw_plan_type);
		/* Warm up.  See issue #1366. */
		fftwf_execute(ctx.ifftwPlan);
	}

	result = hackrf_init_sweep(
		device,
		ctx.frequencies,
		ctx.num_ranges,
		BYTES_PER_BLOCK,
		TUNE_STEP * FREQ_ONE_MHZ,
		OFFSET,
		INTERLEAVED);
	if (result != HACKRF_SUCCESS) {
		fprintf(stderr,
			"hackrf_init_sweep() failed: %s (%d)\n",
			hackrf_error_name(result),
			result);
		free_fftw(&ctx);
		return EXIT_FAILURE;
	}

	result = hackrf_start_rx_sweep(device, rx_callback, &ctx);
	if (result != HACKRF_SUCCESS) {
		fprintf(stderr,
			"hackrf_start_rx_sweep() failed: %s (%d)\n",
			hackrf_error_name(result),
			result);
		free_fftw(&ctx);
		usage();
		return EXIT_FAILURE;
	}

	if (amp) {
		fprintf(stderr, "call hackrf_set_amp_enable(%u)\n", amp_enable);
		result = hackrf_set_amp_enable(device, (uint8_t) amp_enable);
		if (result != HACKRF_SUCCESS) {
			fprintf(stderr,
				"hackrf_set_amp_enable() failed: %s (%d)\n",
				hackrf_error_name(result),
				result);
			usage();
			return EXIT_FAILURE;
		}
	}

	if (antenna) {
		fprintf(stderr, "call hackrf_set_antenna_enable(%u)\n", antenna_enable);
		result = hackrf_set_antenna_enable(device, (uint8_t) antenna_enable);
		if (result != HACKRF_SUCCESS) {
			fprintf(stderr,
				"hackrf_set_antenna_enable() failed: %s (%d)\n",
				hackrf_error_name(result),
				result);
			usage();
			return EXIT_FAILURE;
		}
	}

	gettimeofday(&t_start, NULL);
	time_prev = t_start;

	fprintf(stderr, "Stop with Ctrl-C\n");
	while ((hackrf_is_streaming(device) == HACKRF_TRUE) && !ctx.do_exit) {
		float time_difference;
		m_sleep(POLL_INTERVAL_MS);

		gettimeofday(&time_now, NULL);
		if (TimevalDiff(&time_now, &time_prev) >= 1.0f) {
			uint64_t sweep_snap = atomic_load(&ctx.sweep_count);
			time_difference = TimevalDiff(&time_now, &t_start);
			sweep_rate = (float) sweep_snap / time_difference;

			if (ctx.cal_mode) {
				fprintf(stderr,
					"Calibrating: %" PRIu64 " / %" PRIu64 " sweeps\r",
					sweep_snap, ctx.num_sweeps);
			} else {
				fprintf(stderr,
					"%" PRIu64
					" total sweeps completed, %.2f sweeps/second\n",
					sweep_snap,
					sweep_rate);
			}

			if (atomic_load(&ctx.byte_count) == 0) {
				exit_code = EXIT_FAILURE;
				fprintf(stderr,
					"\nCouldn't transfer any data for one second.\n");
				break;
			}
			atomic_store(&ctx.byte_count, 0);
			time_prev = time_now;
		}
	}

	if (!ctx.cal_mode) {
		fflush(ctx.outfile);
	}

	if (ctx.cal_mode) {
		fprintf(stderr, "\n");
		save_calibration(&ctx);
	}

	result = hackrf_is_streaming(device);
	if (ctx.do_exit) {
		fprintf(stderr, "\nExiting...\n");
	} else {
		fprintf(stderr,
			"\nExiting... hackrf_is_streaming() result: %s (%d)\n",
			hackrf_error_name(result),
			result);
	}

	gettimeofday(&time_now, NULL);
	time_diff = TimevalDiff(&time_now, &t_start);
	uint64_t final_sweeps = atomic_load(&ctx.sweep_count);
	if ((sweep_rate == 0) && (time_diff > 0)) {
		sweep_rate = (float) final_sweeps / time_diff;
	}
	fprintf(stderr,
		"Total sweeps: %" PRIu64 " in %.5f seconds (%.2f sweeps/second)\n",
		final_sweeps,
		time_diff,
		sweep_rate);

	if (device != NULL) {
		result = hackrf_close(device);
		if (result != HACKRF_SUCCESS) {
			fprintf(stderr,
				"hackrf_close() failed: %s (%d)\n",
				hackrf_error_name(result),
				result);
		} else {
			fprintf(stderr, "hackrf_close() done\n");
		}

		hackrf_exit();
		fprintf(stderr, "hackrf_exit() done\n");
	}

	if (!ctx.cal_mode) {
		fflush(ctx.outfile);
		if ((ctx.outfile != NULL) && (ctx.outfile != stdout)) {
			fclose(ctx.outfile);
			ctx.outfile = NULL;
			fprintf(stderr, "fclose() done\n");
		}
	}

	free_fftw(&ctx);
	export_wisdom(fftwWisdomPath);
	fprintf(stderr, "exit\n");
	return exit_code;
}
