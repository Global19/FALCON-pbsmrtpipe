from __future__ import absolute_import
from .. import sys

from pbcore.io import (SubreadSet, HdfSubreadSet, FastaReader, FastaWriter,
                       FastqReader, FastqWriter)
from pypeflow.controller import PypeThreadWorkflow
from pypeflow.data import PypeLocalFile, makePypeLocalFile, fn
from pypeflow.task import PypeTask, PypeThreadTaskBase
import contextlib
import gzip
import logging
import os
import cStringIO

log = logging.getLogger(__name__)

def say(x):
    log.warning(x)
    print 'IN FLOW!'
def run_bam_to_fastx(program_name, fastx_reader, fastx_writer,
                     input_file_name, output_file_name,
                     min_subread_length=0):
    """Copied from pbsmrtpipe/pb_tasks/pacbio.py,
    with minor changes.
    """
    # XXX this is really annoying; bam2fastx needs a --no-gzip feature
    #tmp_out_prefix = tempfile.NamedTemporaryFile().name
    tmp_out_prefix = 'out'
    args = [
        program_name,
        "-o", tmp_out_prefix,
        #'-c', '0', # does not help
        input_file_name,
    ]
    logging.info(" ".join(args))
    sys.system(' '.join(args))
    base_ext = program_name.replace("bam2", "")
    tmp_out = "{p}.{b}.gz".format(p=tmp_out_prefix, b=base_ext)
    assert os.path.isfile(tmp_out), tmp_out
    logging.info("raw output in {!r} to be re-written to {!r} (with min_subread_length={}).".format(
        tmp_out, output_file_name, min_subread_length))
    with gzip.open(tmp_out) as raw_in:
        with fastx_reader(raw_in) as fastx_in:
            with fastx_writer(output_file_name) as fastx_out:
                for rec in fastx_in:
                    if (min_subread_length < 1 or
                        min_subread_length < len(rec.sequence)):
                        fastx_out.writeRecord(rec)
def dict2ini(ofs, options_dict):
    opts = dict()
    for key, val in options_dict.iteritems():
        # Drop comments (keys w/ leading ~).
        if key.startswith('~'):
            continue
        # Strip leading and trailing ws, just in case.
        opts[key] = val
    opts['job_type'] = 'local' # OVERRIDE FOR NOW
    def add(key, val):
        if not key in opts:
            opts[key] = val
    add('input_fofn', 'NA')
    add('target', 'assembly')
    add('sge_option_da', 'NA')
    add('sge_option_la', 'NA')
    add('sge_option_pda', 'NA')
    add('sge_option_pla', 'NA')
    add('sge_option_fc', 'NA')
    add('sge_option_cns', 'NA')
    ofs.write('[General]\n')
    for key, val in sorted(opts.items()):
        ofs.write('{} = {}\n'.format(key, val))

@contextlib.contextmanager
def ContentUpdater(fn):
    """Write new content only if differs from old.
    """
    if os.path.exists(fn):
        with open(fn) as f:
            old_content = f.read()
    else:
        old_content = None
    new_writer = cStringIO.StringIO()
    yield new_writer
    new_content = new_writer.getvalue()
    if new_content != old_content:
        with open(fn, 'w') as f:
            f.write(new_content)
def run_falcon(i_fasta_fn, o_fasta_fn, config_falcon):
    sys.system('rm -f {}'.format(
        o_fasta_fn))
    input_fofn_fn = 'input.fofn'
    with ContentUpdater(input_fofn_fn) as f:
        f.write('{}\n'.format(i_fasta_fn))
    config_falcon['input_fofn'] = input_fofn_fn
    # Write fc.cfg for FALCON.
    fc_cfg_fn = 'fc.cfg'
    with ContentUpdater(fc_cfg_fn) as f:
        dict2ini(f, config_falcon)
    #TODO: Let falcon use logging.json?
    cmd = 'fc_run {}'.format(
        fc_cfg_fn)
    sys.system(cmd)
    sys.system('ln {} {}'.format(
        '2-asm-falcon/p_ctg.fa', o_fasta_fn))
def run_pbalign(reads, asm, alignmentset):
    """
 BlasrService: Align reads to references using blasr.
 BlasrService: Call "blasr /pbi/dept/secondary/siv/testdata/SA3-DS/lambda/2372215/0007_tiny/Analysis_Results/m150404_101626_42267_c100807920800000001823174110291514_s1_p0.all.subreadset.xml /home/UNIXHOME/cdunn/repo/pb/smrtanalysis-client/smrtanalysis/siv/testkit-jobs/sa3_pipelines/polished-falcon-lambda-007-tiny/job_output/tasks/falcon_ns.tasks.task_falcon2_run_asm-0/file.fasta -out /scratch/tmpTbV4Ec/wLCUdL.bam  -bam  -bestn 10 -minMatch 12  -nproc 16  -minSubreadLength 50 -minAlnLength 50  -minPctSimilarity 70 -minPctAccuracy 70 -hitPolicy randombest  -randomSeed 1  -minPctSimilarity 70.0 "
 FilterService: Filter alignments using samFilter.
 FilterService: Call "rm -f /scratch/tmpTbV4Ec/aM1Mor.bam && ln -s /scratch/tmpTbV4Ec/wLCUdL.bam /scratch/tmpTbV4Ec/aM1Mor.bam"
 BamPostService: Sort and build index for a bam file.
 BamPostService: Call "samtools sort -m 4G /scratch/tmpTbV4Ec/aM1Mor.bam /home/UNIXHOME/cdunn/repo/pb/smrtanalysis-client/smrtanalysis/siv/testkit-jobs/sa3_pipelines/polished-falcon-lambda-007-tiny/job_output/tasks/pbalign.tasks.pbalign-0/aligned.subreads.alignmentset"
 BamPostService: Call "samtools index /home/UNIXHOME/cdunn/repo/pb/smrtanalysis-client/smrtanalysis/siv/testkit-jobs/sa3_pipelines/polished-falcon-lambda-007-tiny/job_output/tasks/pbalign.tasks.pbalign-0/aligned.subreads.alignmentset.bam /home/UNIXHOME/cdunn/repo/pb/smrtanalysis-client/smrtanalysis/siv/testkit-jobs/sa3_pipelines/polished-falcon-lambda-007-tiny/job_output/tasks/pbalign.tasks.pbalign-0/aligned.subreads.alignmentset.bam.bai"
 BamPostService: Call "pbindex /home/UNIXHOME/cdunn/repo/pb/smrtanalysis-client/smrtanalysis/siv/testkit-jobs/sa3_pipelines/polished-falcon-lambda-007-tiny/job_output/tasks/pbalign.tasks.pbalign-0/aligned.subreads.alignmentset.bam"
] OutputService: Generating the output XML file
    """
    """
INFO:root:BlasrService: Align reads to references using blasr.
[INFO] 2016-02-04 14:50:25,434Z [root run 178] BlasrService: Align reads to references using blasr.
INFO:root:BlasrService: Call "blasr /pbi/dept/secondary/siv/testdata/SA3-DS/lambda/2372215/0007_tiny/Analysis_Results/m150404_101626_42267_c100807920800000001823174110291514_s1_p0.all.subreadset.xml /home/UNIXHOME/cdunn/repo/pb/smrtanalysis-client/smrtanalysis/siv/testkit-jobs/sa3_pipelines/hgap_lean-lambda-007-tiny/job_output/tasks/falcon_ns.tasks.task_hgap_prepare-0/asm.fasta -out /scratch/tmpwWCCmy/YrpIw_.bam  -bam  -bestn 10 -minMatch 12  -nproc 16  -minSubreadLength 50 -minAlnLength 50  -minPctSimilarity 70 -minPctAccuracy 70 -hitPolicy randombest  -randomSeed 1  -minPctSimilarity 70.0 "
[INFO] 2016-02-04 14:50:25,435Z [root Execute 63] BlasrService: Call "blasr /pbi/dept/secondary/siv/testdata/SA3-DS/lambda/2372215/0007_tiny/Analysis_Results/m150404_101626_42267_c100807920800000001823174110291514_s1_p0.all.subreadset.xml /home/UNIXHOME/cdunn/repo/pb/smrtanalysis-client/smrtanalysis/siv/testkit-jobs/sa3_pipelines/hgap_lean-lambda-007-tiny/job_output/tasks/falcon_ns.tasks.task_hgap_prepare-0/asm.fasta -out /scratch/tmpwWCCmy/YrpIw_.bam  -bam  -bestn 10 -minMatch 12  -nproc 16  -minSubreadLength 50 -minAlnLength 50  -minPctSimilarity 70 -minPctAccuracy 70 -hitPolicy randombest  -randomSeed 1  -minPctSimilarity 70.0 "
INFO:root:FilterService: Filter alignments using samFilter.
[INFO] 2016-02-04 14:51:00,543Z [root run 150] FilterService: Filter alignments using samFilter.
INFO:root:FilterService: Call "rm -f /scratch/tmpwWCCmy/Ba3axn.bam && ln -s /scratch/tmpwWCCmy/YrpIw_.bam /scratch/tmpwWCCmy/Ba3axn.bam"
[INFO] 2016-02-04 14:51:00,544Z [root Execute 63] FilterService: Call "rm -f /scratch/tmpwWCCmy/Ba3axn.bam && ln -s /scratch/tmpwWCCmy/YrpIw_.bam /scratch/tmpwWCCmy/Ba3axn.bam"
INFO:root:BamPostService: Sort and build index for a bam file.
[INFO] 2016-02-04 14:51:00,692Z [root run 100] BamPostService: Sort and build index for a bam file.
INFO:root:BamPostService: Call "samtools sort -m 4G /scratch/tmpwWCCmy/Ba3axn.bam /home/UNIXHOME/cdunn/repo/pb/smrtanalysis-client/smrtanalysis/siv/testkit-jobs/sa3_pipelines/hgap_lean-lambda-007-tiny/job_output/tasks/falcon_ns.tasks.task_hgap_prepare-0/aligned.subreads.alignmentset"
[INFO] 2016-02-04 14:51:00,692Z [root Execute 63] BamPostService: Call "samtools sort -m 4G /scratch/tmpwWCCmy/Ba3axn.bam /home/UNIXHOME/cdunn/repo/pb/smrtanalysis-client/smrtanalysis/siv/testkit-jobs/sa3_pipelines/hgap_lean-lambda-007-tiny/job_output/tasks/falcon_ns.tasks.task_hgap_prepare-0/aligned.subreads.alignmentset"
INFO:root:BamPostService: Call "samtools index /home/UNIXHOME/cdunn/repo/pb/smrtanalysis-client/smrtanalysis/siv/testkit-jobs/sa3_pipelines/hgap_lean-lambda-007-tiny/job_output/tasks/falcon_ns.tasks.task_hgap_prepare-0/aligned.subreads.alignmentset.bam /home/UNIXHOME/cdunn/repo/pb/smrtanalysis-client/smrtanalysis/siv/testkit-jobs/sa3_pipelines/hgap_lean-lambda-007-tiny/job_output/tasks/falcon_ns.tasks.task_hgap_prepare-0/aligned.subreads.alignmentset.bam.bai"
[INFO] 2016-02-04 14:51:10,610Z [root Execute 63] BamPostService: Call "samtools index /home/UNIXHOME/cdunn/repo/pb/smrtanalysis-client/smrtanalysis/siv/testkit-jobs/sa3_pipelines/hgap_lean-lambda-007-tiny/job_output/tasks/falcon_ns.tasks.task_hgap_prepare-0/aligned.subreads.alignmentset.bam /home/UNIXHOME/cdunn/repo/pb/smrtanalysis-client/smrtanalysis/siv/testkit-jobs/sa3_pipelines/hgap_lean-lambda-007-tiny/job_output/tasks/falcon_ns.tasks.task_hgap_prepare-0/aligned.subreads.alignmentset.bam.bai"
INFO:root:BamPostService: Call "pbindex /home/UNIXHOME/cdunn/repo/pb/smrtanalysis-client/smrtanalysis/siv/testkit-jobs/sa3_pipelines/hgap_lean-lambda-007-tiny/job_output/tasks/falcon_ns.tasks.task_hgap_prepare-0/aligned.subreads.alignmentset.bam"
[INFO] 2016-02-04 14:51:12,162Z [root Execute 63] BamPostService: Call "pbindex /home/UNIXHOME/cdunn/repo/pb/smrtanalysis-client/smrtanalysis/siv/testkit-jobs/sa3_pipelines/hgap_lean-lambda-007-tiny/job_output/tasks/falcon_ns.tasks.task_hgap_prepare-0/aligned.subreads.alignmentset.bam"
INFO:root:OutputService: Generating the output XML file
[INFO] 2016-02-04 14:51:13,239Z [root _output 228] OutputService: Generating the output XML file
    """
    args = [
        'pbalign',
        '--verbose',
        #'--debug', # requires 'ipdb'
        #'--profile', # kinda interesting, but maybe slow?
        '--nproc 16',
        '--algorithmOptions "-minMatch 12 -bestn 10 -minPctSimilarity 70.0"',
        #'--concordant',
        '--hitPolicy randombest',
        '--minAccuracy 70.0',
        '--minLength 50',
        reads, asm,
        alignmentset,
    ]
    sys.system(' '.join(args))
def run_gc(alignmentset, referenceset, polished_fastq, options):
    """GenomicConsensus
    TODO: Capture log output? Or figure out how to log to a file.
    """
    args = [
        'variantCaller',
        '--verbose',
        '--log-level INFO',
        #'--debug', # requires 'ipdb'
        #'-j NWORKERS',
        #'--algorithm quiver',
        #'--diploid', # binary
        #'--minConfidence 40',
        #'--minCoverage 5',
        options,
        '--referenceFilename', referenceset,
        '-o', polished_fastq,
        alignmentset,
    ]
    sys.system(' '.join(args))
def run_filterbam(ifn, ofn, config):
    """
    pbcoretools.tasks.filterdataset
    python -m pbcoretools.tasks.filters  run-rtc
        "options": {
            "pbcoretools.task_options.other_filters": "rq >= 0.7",
            "pbcoretools.task_options.read_length": 0
        },
    """
    other_filters = config['pbcoretools'].get('other_filters', 'rq >= 0.7')
    read_length = config['pbcoretools'].get('read_length', 0)
    from pbcoretools.tasks.filters import run_filter_dataset
    log.warning('RUNNING filterbam: %r %r' %(read_length, other_filters))
    rc = run_filter_dataset(ifn, ofn, read_length=read_length, other_filters=other_filters)
    log.warning('FINISHED filterbam(rc=%r): %r %r' %(rc, read_length, other_filters))
def task_filterbam(self):
    #print repr(self.parameters), repr(self.URL), repr(self.foo1)
    #sys.system('touch {}'.format(fn(self.fasta)))
    input_file_name = fn(self.i_dataset)
    output_file_name = fn(self.o_dataset)
    run_filterbam(input_file_name, output_file_name, self.parameters)
def task_bam2fasta(self):
    """
    Same as bam2fasta_nofilter in pbcoretools.
    """
    #print repr(self.parameters), repr(self.URL), repr(self.foo1)
    #sys.system('touch {}'.format(fn(self.fasta)))
    input_file_name = fn(self.dataset)
    output_file_name = fn(self.fasta)
    run_bam_to_fastx('bam2fasta', FastaReader, FastaWriter,
                     input_file_name, output_file_name,
                     min_subread_length=0)
def task_falcon(self):
    input_file_name = fn(self.orig_fasta)
    output_file_name = fn(self.asm_fasta)
    run_falcon(input_file_name, output_file_name, self.parameters['falcon'])
def task_fasta2referenceset(self):
    """Copied from pbsmrtpipe/pb_tasks/pacbio.py:run_fasta_to_referenceset()
    """
    input_file_name = fn(self.fasta)
    output_file_name = fn(self.referenceset)
    sys.system('rm -f {} {}'.format(
        output_file_name,
        input_file_name + '.fai'))
    cmd = 'dataset create --type ReferenceSet --generateIndices {} {}'.format(
            output_file_name, input_file_name)
    sys.system(cmd)
def task_pbalign(self):
    reads = fn(self.dataset)
    referenceset = fn(self.referenceset)
    alignmentset = fn(self.alignmentset)
    run_pbalign(reads, referenceset, alignmentset)
def task_genomic_consensus(self):
    alignmentset = fn(self.alignmentset)
    referenceset = fn(self.referenceset)
    polished_fastq = fn(self.polished_fastq)
    options = self.parameters['variantCaller'].get('options', '')
    run_gc(alignmentset, referenceset, polished_fastq, options)
def task_foo(self):
    log.debug('WARNME1 {!r}'.format(__name__))
    #print repr(self.parameters), repr(self.URL), repr(self.foo1)
    sys.system('touch {}'.format(fn(self.foo2)))

def flow(config):
    parameters = config
    #exitOnFailure=config['stop_all_jobs_on_failure'] # only matter for parallel jobs
    #wf.refreshTargets(exitOnFailure=exitOnFailure)
    #concurrent_jobs = config["pa_concurrent_jobs"]
    #PypeThreadWorkflow.setNumThreadAllowed(concurrent_jobs, concurrent_jobs)
    wf = PypeThreadWorkflow()

    dataset_pfn = makePypeLocalFile(config['pbsmrtpipe']['input_files'][0])
    fdataset_pfn = makePypeLocalFile('filtered.subreadset.xml')
    orig_fasta_pfn = makePypeLocalFile('input.fasta')
    make_task = PypeTask(
            inputs = {"i_dataset": dataset_pfn,},
            outputs = {"o_dataset": fdataset_pfn,},
            parameters = parameters,
            TaskType = PypeThreadTaskBase,
            URL = "task://localhost/filterbam")
    task = make_task(task_filterbam)
    wf.addTask(task)
    wf.refreshTargets()

    orig_fasta_pfn = makePypeLocalFile('input.fasta')
    make_task = PypeTask(
            inputs = {"dataset": fdataset_pfn,},
            outputs =  {"fasta": orig_fasta_pfn,},
            parameters = parameters,
            TaskType = PypeThreadTaskBase,
            URL = "task://localhost/bam2fasta")
    task = make_task(task_bam2fasta)
    wf.addTask(task)
    wf.refreshTargets()

    # We could integrate the FALCON workflow here, but for now we will just execute it.
    asm_fasta_pfn = makePypeLocalFile('asm.fasta')
    make_task = PypeTask(
            inputs =  {"orig_fasta": orig_fasta_pfn,},
            outputs =  {"asm_fasta": asm_fasta_pfn,},
            parameters = parameters,
            TaskType = PypeThreadTaskBase,
            URL = "task://localhost/falcon")
    #task = make_task(task_falcon)
    #wf.addTask(task)
    #wf.refreshTargets()
    run_falcon(fn(orig_fasta_pfn), fn(asm_fasta_pfn), config['falcon'])

    # The reset of the workflow will operate on datasets, not fasta directly.
    referenceset_pfn = makePypeLocalFile('asm.referenceset.xml')
    make_task = PypeTask(
            inputs =  {"fasta": asm_fasta_pfn,},
            outputs = {"referenceset": referenceset_pfn,},
            parameters = parameters,
            TaskType = PypeThreadTaskBase,
            URL = "task://localhost/fasta2referenceset")
    task = make_task(task_fasta2referenceset)
    wf.addTask(task)
    wf.refreshTargets()

    # pbalign (TODO: Look into chunking.)
    alignmentset_pfn = makePypeLocalFile('aligned.subreads.alignmentset.xml')
    """Also produces:
    aligned.subreads.alignmentset.bam
    aligned.subreads.alignmentset.bam.bai
    aligned.subreads.alignmentset.bam.pbi
    """
    make_task = PypeTask(
            inputs = {"dataset": dataset_pfn,
                      "referenceset": referenceset_pfn,},
            outputs = {"alignmentset": alignmentset_pfn,},
            parameters = parameters,
            TaskType = PypeThreadTaskBase,
            URL = "task://localhost/pbalign")
    task = make_task(task_pbalign)
    wf.addTask(task)
    wf.refreshTargets()

    # variantcaller/genomicconsensus (TODO: Look into chunking.)
    polished_fastq_pfn = makePypeLocalFile('polished.fastq')
    """Also produces:
    """
    make_task = PypeTask(
            inputs = {"alignmentset": alignmentset_pfn,
                      "referenceset": referenceset_pfn,},
            outputs = {"polished_fastq": polished_fastq_pfn,},
            parameters = parameters,
            TaskType = PypeThreadTaskBase,
            URL = "task://localhost/genomic_consensus")
    task = make_task(task_genomic_consensus)
    wf.addTask(task)
    wf.refreshTargets()

    #return
    ##############

    if not os.path.exists('foo.bar1'):
        sys.system('touch foo.bar1')
    foo_fn1 = makePypeLocalFile('foo.bar1')
    foo_fn2 = makePypeLocalFile('foo.bar2')
    make_task = PypeTask(
            inputs = {"foo1": foo_fn1,},
            outputs =  {"foo2": foo_fn2,},
            parameters = parameters,
            TaskType = PypeThreadTaskBase,
            URL = "task://localhost/foo")
    task = make_task(task_foo)
    wf.addTask(task)
    wf.refreshTargets()

    #raise Exception('hi')
