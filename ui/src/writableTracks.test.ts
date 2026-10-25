import {describe,it,expect} from 'vitest';
import {writableTracks} from './library';

const tracks=[
 {id:'a',cues:[{review:'approved'},{review:'proposed'}]},
 {id:'b',cues:[{review:'proposed'},{review:'rejected'}]},
 {id:'c',cues:[{review:'delete-approved'},{review:'approved'}]},
];

describe('batch cue write selection',()=>{
 it('keeps only selected tracks with decisions rekordbox acts on',()=>{
  expect(writableTracks(tracks,['a','b','c'])).toEqual({ids:['a','c'],cues:3});
 });
 it('ignores tracks outside the selection',()=>{
  expect(writableTracks(tracks,['b'])).toEqual({ids:[],cues:0});
 });
});
